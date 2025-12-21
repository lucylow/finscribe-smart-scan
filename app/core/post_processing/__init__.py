"""
Post-processing intelligence layer for financial document extraction.
"""

from .intelligence import FinancialPostProcessor
# Also import from the module (post_processing.py) if it exists
try:
    import sys
    import importlib.util
    spec = importlib.util.spec_from_file_location("post_processing_module", 
                                                   __file__.replace("__init__.py", "../post_processing.py"))
    if spec and spec.loader:
        post_processing_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(post_processing_module)
        if hasattr(post_processing_module, 'FinancialDocumentPostProcessor'):
            FinancialDocumentPostProcessor = post_processing_module.FinancialDocumentPostProcessor
            __all__ = ['FinancialPostProcessor', 'FinancialDocumentPostProcessor']
        else:
            __all__ = ['FinancialPostProcessor']
    else:
        __all__ = ['FinancialPostProcessor']
except Exception:
    __all__ = ['FinancialPostProcessor']


