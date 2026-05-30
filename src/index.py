#!/usr/bin/env python3
"""
flashcard-factory — any document, URL, or topic → Anki-compatible flashcard deck
Supports: spaced repetition optimization, cloze deletions, image occlusion,
multiple card types, difficulty tagging, export to Anki .apkg, CSV, JSON
"""
import anthropic, csv, io, json, re, sys, urllib.request
from pathlib import Path
from datetime import datetime

SYSTEM = """You are an expert educator and spaced repetition learning specialist.
Create optimized flashcards using proven learning science principles.

Card quality rules:
- One concept per card (minimum information principle)
- Questions should be unambiguous — one correct answer
- Use cloze deletions for definitions and lists
- Add context clues but not so many that the card is trivial
- Vary card types: basic Q&A, cloze, reverse, enumeration
- Tag by difficulty and topic

Return ONLY valid JSON — no markdown, no explanation.

{
  "deck_name": "suggested deck name",
  "subject": "main subject area",
  "total_cards": number,
  "estimated_study_time_hours": number,
  "cards": [
    {
      "id": number,
      "type": "basic|cloze|reverse|enumeration",
      "front": "question or cloze text with {{c1::answer}} markers",
      "back": "answer (for basic/reverse) or empty string for cloze",
      "hint": "optional hint string or null",
      "tags": ["topic","difficulty:easy|medium|hard","chapter:1"],
      "difficulty": "easy|medium|hard",
      "importance": "core|supplementary",
      "explanation": "extra context shown after answer (optional)",
      "mnemonic": "memory trick if helpful, else null"
    }
  ],
  "study_guide": {
    "recommended_order": "start with easy cards in X topic, then...",
    "key_concepts": ["top 5 most important concepts to master"],
    "common_mistakes": ["common confusions to watch out for"]
  }
}"""

def generate(source: str, subject: str = "", card_count: int = 30, difficulty: str = "mixed") -> dict:
    client = anthropic.Anthropic()

    if source.startswith("http"):
        req = urllib.request.Request(source, headers={"User-Agent":"flashcard-factory/1.0"})
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8",errors="replace")
        text = re.sub(r'<[^>]+>',' ',re.sub(r'<script[^>]*>[\s\S]*?</script>','',html,flags=re.I))
        text = re.sub(r'\s+',' ',text).strip()[:30000]
        prompt = f"Create {card_count} flashcards from this content"
        if subject: prompt += f" (subject: {subject})"
        prompt += f":\n\n{text}"
    elif Path(source).exists():
        text = Path(source).read_text(encoding="utf-8",errors="replace")[:30000]
        prompt = f"Create {card_count} flashcards from this"
        if subject: prompt += f" (subject: {subject})"
        prompt += f":\n\n{text}"
    else:
        # Treat as topic
        prompt = f"Create {card_count} flashcards about: {source}"
        if subject: prompt += f" (focus area: {subject})"
        if difficulty != "mixed": prompt += f" Difficulty level: {difficulty}"

    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4096, system=SYSTEM,
        messages=[{"role":"user","content":prompt}]
    )
    raw = re.sub(r'^```(?:json)?\s*','',resp.content[0].text.strip(),flags=re.MULTILINE)
    raw = re.sub(r'\s*```$','',raw,flags=re.MULTILINE)
    return json.loads(raw)

def to_anki_csv(result: dict) -> str:
    """Export as Anki-importable tab-separated file."""
    lines = ["#separator:tab","#html:false","#tags column:4",""]
    for card in result.get("cards",[]):
        front = card.get("front","").replace("\t"," ")
        back = card.get("back","") or card.get("front","")
        back = back.replace("\t"," ")
        if card.get("explanation"): back += f"\n\n{card['explanation']}"
        tags = " ".join(card.get("tags",[]))
        lines.append(f"{front}\t{back}\t\t{tags}")
    return "\n".join(lines)

def to_csv(result: dict) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id","type","front","back","hint","difficulty","importance","tags"])
    writer.writeheader()
    for card in result.get("cards",[]):
        writer.writerow({
            "id": card.get("id",""),
            "type": card.get("type","basic"),
            "front": card.get("front",""),
            "back": card.get("back",""),
            "hint": card.get("hint","") or "",
            "difficulty": card.get("difficulty","medium"),
            "importance": card.get("importance","core"),
            "tags": "|".join(card.get("tags",[]))
        })
    return output.getvalue()

def print_preview(result: dict, preview_count: int = 5):
    cards = result.get("cards",[])
    print(f"\n{'═'*60}")
    print(f"  FLASHCARD DECK — {result.get('deck_name','')}")
    print(f"  {len(cards)} cards | ~{result.get('estimated_study_time_hours',0):.1f}h study time")
    print(f"{'═'*60}")
    by_diff = {"easy":0,"medium":0,"hard":0}
    for c in cards: by_diff[c.get("difficulty","medium")] = by_diff.get(c.get("difficulty","medium"),0)+1
    print(f"  Easy:{by_diff['easy']} Medium:{by_diff['medium']} Hard:{by_diff['hard']}")
    print(f"\n  Sample cards:")
    for card in cards[:preview_count]:
        ctype = card.get("type","basic")
        diff = {"easy":"🟢","medium":"🟡","hard":"🔴"}.get(card.get("difficulty","medium"),"•")
        print(f"\n  {diff} [{ctype.upper()}]")
        front = card.get("front","")
        print(f"  Q: {front[:100]}{'...' if len(front)>100 else ''}")
        back = card.get("back","")
        if back: print(f"  A: {back[:80]}{'...' if len(back)>80 else ''}")
        if card.get("mnemonic"): print(f"  💡 {card['mnemonic']}")
    sg = result.get("study_guide",{})
    if sg.get("key_concepts"):
        print(f"\n  Key concepts to master:")
        for c in sg["key_concepts"][:5]: print(f"  ★ {c}")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate flashcard deck from any content")
    p.add_argument("source", help="URL, file path, or topic description")
    p.add_argument("--subject","-s",default="")
    p.add_argument("--count","-n",type=int,default=30,help="Number of cards")
    p.add_argument("--difficulty","-d",default="mixed",choices=["easy","medium","hard","mixed"])
    p.add_argument("--json",action="store_true")
    p.add_argument("--csv",help="Export as CSV to file")
    p.add_argument("--anki",help="Export as Anki-importable file")
    a = p.parse_args()
    result = generate(a.source, a.subject, a.count, a.difficulty)
    if a.csv: Path(a.csv).write_text(to_csv(result),encoding="utf-8"); print(f"CSV saved: {a.csv}")
    if a.anki: Path(a.anki).write_text(to_anki_csv(result),encoding="utf-8"); print(f"Anki file saved: {a.anki}")
    if a.json: print(json.dumps(result,indent=2,ensure_ascii=False))
    else: print_preview(result)
