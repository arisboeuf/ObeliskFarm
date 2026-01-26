# ObeliskFarm - Design Guidelines

This document contains design principles and guidelines for the ObeliskFarm Calculator GUI. All future changes and additions should follow these guidelines.

## Language & Communication

### Primary Language
- **English** for all user-facing text
- Code comments can be in English or German
- Variable names and function names in English

### Tone
- Clear and concise
- Technical but accessible
- No unnecessary emojis (only use if explicitly requested)

## GUI Design Principles

### Color Scheme & Visual Separation

**Section Background Colors:**
- **Freebie Section**: Light Blue `#E3F2FD` with `RIDGE` border
- **Founder Supply Drop Section**: Light Green `#E8F5E9` with `RIDGE` border
- **Founder Bomb Section**: Light Orange/Beige `#FFF3E0` with `RIDGE` border

**Purpose**: Each major section must be visually distinct through color-coded backgrounds to improve readability and structure.

### Icons & Sprites

**Integration**:
- All sprite icons should be loaded from `sprites/` folder
- Icons should be resized appropriately for context (16-32px typical)
- Always include fallback behavior if sprite cannot be loaded
- Add white background with border for better visibility where needed

**Current Sprites**:
- `gem.png` - Main window icon
- `skill_shard.png` - Skill Shards section (16x16)
- `stonks_tree.png` - Stonks checkbox (20x20)
- `gamespeed2x.png` - Lootbug Analyzer 2x Speed (32x32, white bg + border)
- `founderbomb.png` - Founder Bomb section (20x20)
- `lootbug.png` - Lootbug Analyzer button (32x32)

### Tooltips

**Style Requirements**:
```
- Modern white background (#FFFFFF)
- Dark gray shadow frame (#2C3E50)
- No standard yellow tooltip appearance
- Rich text formatting support
- Proper padding (12px horizontal, 8px vertical)
```

**Formatting**:
- **Headers**: Bold, blue (#1976D2), font size 10pt
- **Subheaders**: Bold, font size 9pt
- **Normal text**: Regular, font size 9pt
- **Percentages**: Green (#2E7D32), font size 9pt
- Structure content with clear sections and line breaks

**Content Guidelines**:
- Always group related information under clear headers
- Use bullet points for lists
- Include percentages where relevant (especially for contributions)
- Format: "Value (Percentage%)" for contribution displays
- Example: "• Gems (20-40): 15.3 Gems (22.5%)"

### Layout & Spacing

**Compact Design**:
- Minimize unnecessary padding
- Use separators to create visual breaks
- Sections should be visually grouped but not cramped

**Responsive Behavior**:
- Main window should be resizable
- Charts and results sections should expand/contract with window
- Minimum window size: 1000x600
- Default size: 1400x800

### Typography

**Font Family**: Arial (cross-platform compatibility)

**Font Sizes**:
- Main headers: 16pt bold
- Section headers: 10-12pt bold
- Labels: 9pt regular
- Tooltips: 9pt regular (headers 10pt bold)
- Small text/hints: 8pt

### Data Display

**Contributions & Statistics**:
- Always show absolute values AND percentages
- Format: `{value:.1f} Gems ({percentage:.1f}%)`
- Use color coding for emphasis:
  - Positive values: Green
  - Negative values: Red
  - Percentages: Green (#2E7D32)

**Bar Charts**:
- Show values on top of bars
- Include percentages in parentheses
- Use stacked bars for components
- Legend should be clear and positioned top-right
- Grid lines for Y-axis only

## Component-Specific Guidelines

### Lootbug Analyzer Window

**Info Display**:
- Important info should appear only on hover (tooltip)
- Use "ℹ️ Hinweis (Hover für Details)" pattern for collapsible information
- Never display large info boxes permanently if they can be shown on hover

**Status Indicators**:
- Success/Positive: Green with ✅
- Failure/Negative: Red with ❌
- Use clear visual separation between status and details

### Parameter Input

**Background Colors**:
- All input labels must match their section's background color
- Use `bg_color` parameter in `create_entry()` function
- Maintain consistent styling within each section

**Entry Fields**:
- Standard width: 20 characters
- Always use ttk.Entry for consistency
- Support auto-calculation with 500ms delay

### Results Display

**Total Display**:
- Always bold and prominent
- Larger font size than detail items
- Clear separator before and after

**Gift-EV Section**:
- Hover tooltip with dynamic contributions
- Show breakdown with percentages
- Update dynamically on recalculation

## Code Style

### GUI Code Organization

```python
# Preferred pattern for sections with colored backgrounds:
container = tk.Frame(parent, background="#COLOR", relief=tk.RIDGE, borderwidth=2)
container.pack(fill=tk.X, padx=3, pady=(3, 8))

header_frame = tk.Frame(container, background="#COLOR")
header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

content_frame = tk.Frame(container, background="#COLOR")
content_frame.pack(fill=tk.X, padx=5, pady=5)
```

### Tooltip Creation

```python
# Always use create_tooltip() or create_dynamic_gift_tooltip()
# Never use standard tk tooltip or simple Label for info display
self.create_tooltip(widget, formatted_text)
```

### Icon Loading Pattern

```python
try:
    icon_path = Path(__file__).parent / "sprites" / "icon.png"
    if icon_path.exists():
        icon_image = Image.open(icon_path)
        icon_image = icon_image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        self.icon_photo = ImageTk.PhotoImage(icon_image)
        # Use icon...
except:
    pass  # Graceful fallback
```

## Testing & Quality

### Visual Testing
- Test all tooltips for proper formatting
- Verify color contrast and readability
- Check sprite visibility on different backgrounds
- Ensure responsive behavior at various window sizes

### Accessibility
- Maintain sufficient color contrast
- Use clear, readable fonts
- Ensure clickable elements have proper cursor feedback
- Tooltips should appear close to cursor but not obscure content

## Version History

### v1.0 (2026-01-18)
- Initial design guidelines document
- Established color scheme for sections
- Defined tooltip styling standards
- Documented sprite integration patterns
- Set typography standards
- Defined contribution display format with percentages
