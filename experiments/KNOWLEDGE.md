# KNOWLEDGE — durable facts for ML_Optimize_Research_Agent

Settled facts worth not re-deriving. Add as they're confirmed.

## Presentation / slide deck convention (yilin's research talks)
- The project's discussion deck is `notes_discussion.pptx` (attached to issue YIL-113, attachment id 019f5f0b).
  16:9, master carries Purdue + CaRT branding.
- **Literature-review slide style = its slide 3 ("LR1" = MTPOMO/multi-task VRP FM).** Layout `1_自定义版式`:
  placeholder idx 11 = white banner title, idx 10 = big subtitle bullet ("LR1"); body = a plain textbox
  ('TextBox 4'), font **Amasis MT Pro**, structure **framing sentence(s) → GAP → "Method" → indented bullets**.
- To generate matching slides: clone slide 3 and swap text (see
  `experiments/20260714-op-fm-survey/build_slides.py`). Keep header ≤ ~24 chars and subtitle short (like "LR1")
  or they wrap over the body. Body 15/14 pt keeps dense slides above the footer.

## Env
- `conda activate torchnn` before running Python. python-pptx installed there (for deck building).
- Deck render check: `soffice --headless --convert-to pdf ...` then `pdftoppm -png`.
