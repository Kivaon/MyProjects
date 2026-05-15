# Detailed PyMuPDF Extraction Process for 22.pdf

## Process Overview

### Step 1: Word Extraction
```python
words_raw = page.get_text("words")
# Extracts: [(x0, y0, x1, y1, text), ...]
```

### Step 2: Word Processing
```python
words = [
    {
        "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3], "text": w[4]
    }
    for w in words_raw if w[4].strip()
]
```

### Step 3: Line Grouping
```python
def group_words_to_lines_pymupdf(words, y_tol=3):
    # Groups words by Y position with 3px tolerance
    # Sorts words within lines by direction (RTL/LTR)
```

### Step 4: Region Segmentation
```python
def split_lines_into_vertical_regions_pymupdf(lines, page_width, gap_threshold=22, width_change_ratio=0.22):
    # Splits based on:
    # - Vertical gaps > 22px
    # - Width changes > 22%
```

### Step 5: Column Detection
```python
def detect_columns_in_region_pymupdf(lines, page_width, min_lines_for_multicol=4):
    # Analyzes:
    # - Average line width (>62% = 1 column)
    # - X-center clustering with 12% page width gaps
```

### Step 6: Column Assignment
```python
def assign_lines_to_columns_pymupdf(lines, columns, page_width):
    # Divides lines by X position ranges
    # Sorts lines within columns top to bottom
```

### Step 7: Text Assembly (RTL Order)
```python
# For RTL: Right column first, then Left column
if direction == "RTL":
    ordered_columns = list(reversed(column_groups))
else:
    ordered_columns = column_groups

# Output complete columns as blocks
for col in ordered_columns:
    col_sorted = sorted(col, key=lambda l: l["y0"])
    col_text = "\n".join(line["text"] for line in col_sorted)
    region_text_parts.append(col_text)
```

---

## Example Processing Flow

### Input: 22.pdf Page 1

#### Words Extracted:
```
[(100, 50, 150, 60, " Right column text "),
 (300, 50, 350, 60, " Left column text "),
 (100, 70, 150, 80, " More right text "),
 (300, 70, 350, 80, " More left text ")]
```

#### Lines Grouped:
```
Line 1: [
    {"text": " Right column text ", "x0": 100, "x1": 150},
    {"text": " Left column text ", "x0": 300, "x1": 350}
]
Line 2: [
    {"text": " More right text ", "x0": 100, "x1": 150},
    {"text": " More left text ", "x0": 300, "x1": 350}
]
```

#### Direction Detection:
```
Sample text: " Right column text  Left column text "
RTL chars: 15, LTR chars: 0
Direction: RTL
```

#### Column Detection:
```
Average line width: 50/400 = 12.5% (< 62%)
X-centers: [125, 325, 125, 325]
Gaps: [200] (> 12% of page width = 48px)
Columns: 2
```

#### Column Assignment:
```
Right column (X < 225): Lines with x-center < 225
Left column (X >= 225): Lines with x-center >= 225
```

#### RTL Order Output:
```
RIGHT COLUMN BLOCK:
Right column text 
More right text 

LEFT COLUMN BLOCK:
Left column text 
More left text 
```

---

## Key Improvements Over pdfplumber

### 1. Adaptive Region Detection
- **Old**: Fixed 40px zones
- **New**: Gap + width change detection

### 2. Better Column Detection
- **Old**: Simple gap > 35px
- **New**: Width ratio + center clustering

### 3. Proper RTL Column Order
- **Old**: Mixed lines from columns
- **New**: Complete right column, then complete left column

### 4. Advanced Direction Detection
- **Old**: Basic Unicode ranges
- **New**: Unicode + bidi properties

---

## Processing Results

### Region 4: 2 columns, RTL, 8 lines
```
RIGHT COLUMN:
[Complete right column text block]

LEFT COLUMN:  
[Complete left column text block]
```

### Region 13: 2 columns, RTL, 7 lines
```
RIGHT COLUMN:
[Complete right column text block]

LEFT COLUMN:
[Complete left column text block]
```

This ensures proper reading order for RTL documents!
