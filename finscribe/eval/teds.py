"""
Table Structure Recognition (TEDS) evaluation
"""

from typing import Optional


def teds_score(pred_html: str, gt_html: str) -> float:
    """
    Calculates TEDS (Tree-Edit-Distance-based Similarity) score for table structure.
    
    Args:
        pred_html: Predicted table as HTML string
        gt_html: Ground truth table as HTML string
        
    Returns:
        TEDS score between 0.0 and 1.0
    """
    try:
        # Try to import TEDS library
        try:
            from teds import TEDS
            teds = TEDS()
            return teds.evaluate(pred_html, gt_html)
        except ImportError:
            # Fallback: simple structure comparison
            return _simple_table_similarity(pred_html, gt_html)
    except Exception as e:
        print(f"Error calculating TEDS: {e}")
        return 0.0


def _simple_table_similarity(pred_html: str, gt_html: str) -> float:
    """
    Simple fallback table similarity when TEDS library is not available.
    Compares row and column counts.
    """
    import re
    
    # Count rows
    pred_rows = len(re.findall(r"<tr", pred_html))
    gt_rows = len(re.findall(r"<tr", gt_html))
    
    # Count columns (from first row)
    pred_cols_match = re.search(r"<tr[^>]*>(.*?)</tr>", pred_html, re.DOTALL)
    gt_cols_match = re.search(r"<tr[^>]*>(.*?)</tr>", gt_html, re.DOTALL)
    
    pred_cols = len(re.findall(r"<t[dh]", pred_cols_match.group(1) if pred_cols_match else ""))
    gt_cols = len(re.findall(r"<t[dh]", gt_cols_match.group(1) if gt_cols_match else ""))
    
    # Calculate similarity
    row_sim = 1.0 - abs(pred_rows - gt_rows) / max(gt_rows, 1)
    col_sim = 1.0 - abs(pred_cols - gt_cols) / max(gt_cols, 1)
    
    return (row_sim + col_sim) / 2.0


def table_to_html(table_data: list, headers: Optional[list] = None) -> str:
    """
    Converts table data (list of dicts) to HTML table string.
    
    Args:
        table_data: List of row dictionaries
        headers: Optional list of header names (if None, inferred from first row)
        
    Returns:
        HTML table string
    """
    if not table_data:
        return "<table></table>"
    
    if headers is None:
        headers = list(table_data[0].keys())
    
    html = "<table><thead><tr>"
    for header in headers:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for row in table_data:
        html += "<tr>"
        for header in headers:
            value = row.get(header, "")
            html += f"<td>{value}</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html


