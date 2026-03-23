#!/usr/bin/env python3
"""
Comment Manager — Monitors comments and creates draft replies for approval.

This module:
  1. Fetches new (unreplied) comments from the channel
  2. Uses Claude AI to draft contextual, on-brand replies
  3. Saves drafts to growth/drafts/ as JSON for human review
  4. On approval, posts the reply via YouTube API

IMPORTANT: No comment is ever posted automatically.
           All replies require explicit human approval.

Usage:
    python -m growth.comment_manager check          # fetch & draft new replies
    python -m growth.comment_manager list            # show pending drafts
    python -m growth.comment_manager approve DRAFT_ID  # approve and post a draft
    python -m growth.comment_manager approve --all   # approve all pending drafts
    python -m growth.comment_manager reject DRAFT_ID   # delete a draft
"""

import argparse
import json
import os
import sys
from datetime import datetime

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from growth import config, auth

DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "drafts")
CHANNEL_ID = config.channel_id()

REPLY_STYLE = """\
You are replying as Sonat Mundi, a world music channel.
Voice: warm, grateful, mystical but not pretentious. Short and genuine.
Rules:
- Always thank the listener
- If they mention a specific track, acknowledge it
- If they ask a question, answer helpfully
- Use 1-2 relevant emojis max (🙏 ✨ 🌍 🎵)
- Keep replies 1-3 sentences
- Sign off naturally (no forced branding)
- If the comment is negative, respond gracefully and constructively
- If it's spam, return SKIP
- Write in the SAME LANGUAGE as the comment"""


def fetch_unreplied_comments(youtube, max_results=50):
    """Fetch comments on channel videos that haven't been replied to."""
    # Get channel uploads
    ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl_resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_id, maxResults=20
    ).execute()
    video_ids = [item["contentDetails"]["videoId"] for item in pl_resp["items"]]

    unreplied = []
    for vid in video_ids:
        try:
            threads = youtube.commentThreads().list(
                part="snippet",
                videoId=vid,
                order="time",
                maxResults=max_results,
            ).execute()
        except Exception as e:
            print(f"  Skipping video {vid}: {e}")
            continue

        for thread in threads.get("items", []):
            snippet = thread["snippet"]
            top = snippet["topLevelComment"]["snippet"]

            # Skip if already replied (totalReplyCount > 0 means someone replied)
            if snippet["totalReplyCount"] > 0:
                continue

            # Skip our own comments
            if top["authorChannelId"]["value"] == CHANNEL_ID:
                continue

            unreplied.append({
                "thread_id": thread["id"],
                "video_id": vid,
                "author": top["authorDisplayName"],
                "text": top["textDisplay"],
                "published": top["publishedAt"],
                "like_count": top["likeCount"],
            })

    return unreplied


def draft_replies(comments):
    """Use Claude AI to draft replies for each comment."""
    if not comments:
        print("No unreplied comments found.")
        return []

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    comments_text = "\n".join(
        f"[{c['thread_id']}] @{c['author']}: {c['text']}"
        for c in comments
    )

    prompt = f"""{REPLY_STYLE}

Draft replies for these YouTube comments. Return a JSON array:
[{{
  "thread_id": "...",
  "reply": "your draft reply",
  "sentiment": "positive/neutral/negative/spam",
  "priority": "high/medium/low"
}}]

If a comment is spam, set reply to "SKIP".
If a comment is in a foreign language, reply in that language.

Comments:
{comments_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse JSON from response
    text = message.content[0].text
    # Find JSON array in response
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []


def save_drafts(comments, replies):
    """Save draft replies to disk for human review."""
    os.makedirs(DRAFTS_DIR, exist_ok=True)

    comment_map = {c["thread_id"]: c for c in comments}
    saved = 0

    for reply in replies:
        if reply.get("reply") == "SKIP":
            continue

        tid = reply["thread_id"]
        comment = comment_map.get(tid, {})

        draft = {
            "draft_id": f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{saved}",
            "thread_id": tid,
            "video_id": comment.get("video_id", ""),
            "author": comment.get("author", ""),
            "comment_text": comment.get("text", ""),
            "draft_reply": reply["reply"],
            "sentiment": reply.get("sentiment", "neutral"),
            "priority": reply.get("priority", "medium"),
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }

        path = os.path.join(DRAFTS_DIR, f"{draft['draft_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(draft, f, indent=2, ensure_ascii=False)
        saved += 1

    print(f"Saved {saved} draft replies to {DRAFTS_DIR}")
    return saved


def list_drafts():
    """List all pending draft replies."""
    if not os.path.exists(DRAFTS_DIR):
        print("No drafts directory found.")
        return

    pending = []
    for fname in sorted(os.listdir(DRAFTS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(DRAFTS_DIR, fname), encoding="utf-8") as f:
            draft = json.load(f)
        if draft.get("status") == "pending":
            pending.append(draft)

    if not pending:
        print("No pending drafts.")
        return

    print(f"\n{'='*70}")
    print(f"  PENDING COMMENT DRAFTS ({len(pending)})")
    print(f"{'='*70}\n")

    for d in pending:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            d["priority"], "⚪"
        )
        print(f"  {priority_icon} {d['draft_id']}")
        print(f"     Video: {d['video_id']}")
        print(f"     @{d['author']}: {d['comment_text'][:80]}")
        print(f"     Draft: {d['draft_reply']}")
        print(f"     Sentiment: {d['sentiment']} | Priority: {d['priority']}")
        print()


def approve_draft(draft_id, youtube=None):
    """Approve and post a draft reply."""
    path = os.path.join(DRAFTS_DIR, f"{draft_id}.json")
    if not os.path.exists(path):
        print(f"Draft not found: {draft_id}")
        return False

    with open(path, encoding="utf-8") as f:
        draft = json.load(f)

    if draft["status"] != "pending":
        print(f"Draft {draft_id} is already {draft['status']}.")
        return False

    if youtube is None:
        youtube = auth.youtube_service()

    # Post the reply
    try:
        youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": draft["thread_id"],
                    "textOriginal": draft["draft_reply"],
                }
            },
        ).execute()

        draft["status"] = "approved"
        draft["approved_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(draft, f, indent=2, ensure_ascii=False)

        print(f"  ✓ Posted reply to @{draft['author']}")
        return True

    except Exception as e:
        print(f"  ✗ Failed to post reply: {e}")
        return False


def reject_draft(draft_id):
    """Reject/delete a draft."""
    path = os.path.join(DRAFTS_DIR, f"{draft_id}.json")
    if os.path.exists(path):
        os.remove(path)
        print(f"  ✓ Deleted draft: {draft_id}")
    else:
        print(f"  Draft not found: {draft_id}")


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi Comment Manager")
    parser.add_argument("action", choices=["check", "list", "approve", "reject"],
                        help="Action to perform")
    parser.add_argument("target", nargs="?", help="Draft ID or --all")
    args = parser.parse_args()

    if args.action == "check":
        youtube = auth.youtube_service()
        print("Fetching unreplied comments...")
        comments = fetch_unreplied_comments(youtube)
        print(f"Found {len(comments)} unreplied comments.")

        if comments:
            print("Generating AI draft replies...")
            replies = draft_replies(comments)
            save_drafts(comments, replies)
            print("\nRun 'python -m growth.comment_manager list' to review drafts.")

    elif args.action == "list":
        list_drafts()

    elif args.action == "approve":
        if args.target == "--all":
            youtube = auth.youtube_service()
            for fname in sorted(os.listdir(DRAFTS_DIR)):
                if fname.endswith(".json"):
                    draft_id = fname.replace(".json", "")
                    approve_draft(draft_id, youtube)
        elif args.target:
            approve_draft(args.target)
        else:
            print("Specify a draft ID or --all")

    elif args.action == "reject":
        if args.target:
            reject_draft(args.target)
        else:
            print("Specify a draft ID to reject.")


if __name__ == "__main__":
    main()
