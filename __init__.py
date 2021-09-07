import sys
from . import ontotrees
from .recommendations import Recommendation

sys.modules["ontotrees"] = ontotrees
