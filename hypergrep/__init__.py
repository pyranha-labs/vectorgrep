"""Libraries for reading raw text files with Intel Hyperscan."""

from hypergrep.utils import CALLBACK_TYPE
from hypergrep.utils import HS_FLAG_CASELESS
from hypergrep.utils import HS_FLAG_DOTALL
from hypergrep.utils import HS_FLAG_MULTILINE
from hypergrep.utils import HS_FLAG_SINGLEMATCH
from hypergrep.utils import Result
from hypergrep.utils import check_compatibility
from hypergrep.utils import configure_libraries
from hypergrep.utils import grep
from hypergrep.utils import prepare_patterns
from hypergrep.utils import scan

__version__ = "3.0.0"
