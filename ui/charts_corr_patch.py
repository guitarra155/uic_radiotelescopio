"""Parche: corrige la firma corrupta en chart_correlogram_spectrogram."""
with open(r"ui\charts.py", "r", encoding="utf-8") as f:
    text = f.read()

# Reemplazar cualquier variante corrupta de la firma
import re
text = re.sub(
    r"def chart_correlogram_spectrogram\(result: dict\) [^\n]+ str:",
    "def chart_correlogram_spectrogram(result: dict) -> str:",
    text,
)

with open(r"ui\charts.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Parche aplicado OK")
