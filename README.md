# Luxor_Like
A small Luxor inspired drawing API for Python

"Hey Red, why not just use Luxor instead of building a whole API for Python?"
- Cause I'm lazy

"Hey Red, wouldn't it be less work to just use Luxor?"
- Probably. No further questions.

  ex:
from luxor_like import png, sethue, circle, O

with png("example.png", 400, 400):
    sethue("black")
    circle(O, 100, stroke=True)

