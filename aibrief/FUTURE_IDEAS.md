# Future Ideas to Implement

## 1. Constraint-Based PDF Layout Engine

Replace the current hardcoded PDF layout with an intelligent, constraint-based system
that produces visually diverse, professional layouts every run.

### Architecture: Two-Phase Algorithm

#### Phase 1: Object Builder (Construction)

Takes raw content elements (text, images) and constructs each **PlaceableObject**.

**Steps:**
1. **Extract raw content** from the brief (headlines, bullets, quotes, stats, images)
2. **Group elements** using heuristic rules (e.g. a `point` and its `detail` combine into one block)
3. **Enforce Rule of Odds** — ensure 3, 5, or 7 content objects per page (odd counts feel more natural)
4. **Assign importance** (1–10) based on:
   - Content type (headline > quote > bullet > label)
   - Text length (shorter = punchier = higher)
   - Presence of numbers or statistics
   - Position in content hierarchy (first bullet gets a boost)
5. **Equal initial size** — every object starts at the same base share of the fill area
6. **Golden Ratio scaling** — importance determines a multiplier via PHI:
   - `exponent = (importance - 5.5) / 4.5` → maps 1→-1.0, 10→+1.0
   - `weight = PHI ^ exponent`
   - Higher importance → larger block, lower → smaller
7. **Aspect ratio** decided by content type:
   - Headlines: wide and short (3:1 – 5:1)
   - Stats: nearly square (1.2:1 – 1.8:1)
   - Bullets: depends on text length
8. **Container styling** — every block gets a VISIBLE container:
   - Shape (rect, rounded_rect, pill)
   - Background color from theme palette with opacity 0.35–0.95
   - Border (accent left-bar for quotes, bottom-bar for headlines, full border for stats)
   - Corner radius, padding

**Decision Classification:**
| Decision | Type | Information Needed |
|----------|------|--------------------|
| Grouping elements | Heuristic | Content type pairs, semantic proximity |
| Importance rating | Heuristic | Content type, text length, has numbers, position |
| Base size (equal share) | Rule-based | Object count, target fill |
| Golden ratio multiplier | Rule-based | Importance score |
| Aspect ratio | Heuristic | Content type, text length |
| Container shape | Heuristic | Content type, importance, theme mood |
| Background color | Rule-based | Theme palette + importance |
| Border style | Heuristic | Content type, design theme |

#### Phase 2: Object Placer (Positioning)

Takes fully constructed, sized, and styled PlaceableObjects and determines `(x, y)` coordinates.

**Steps:**
1. **Golden Ratio grid** on the canvas:
   - Divide safe zone by PHI vertically and horizontally
   - Creates 4 focal points at grid intersections (golden spiral termination points)
2. **Place highest-importance object** at the primary focal point
3. **Symmetry pairing** — find similar objects (same type, similar size) and mirror around center axis
4. **Place remaining objects** by scanning candidate positions (center, left-aligned, right-aligned at various Y fractions)
5. **Enforce hard constraints:**
   - No overlap between any two objects
   - Minimum 3% of screen area gap between blocks
   - Nothing within 2% of total area from edges
6. **Gestalt proximity** — objects in the same semantic group stay closer together

**Decision Classification:**
| Decision | Type | Information Needed |
|----------|------|--------------------|
| Golden grid layout | Rule-based | Canvas size, PHI |
| Focal point placement | Rule-based | Importance ranking |
| Symmetry pairing | Rule-based | Content type + size similarity |
| Position candidates | Heuristic | Importance, content type, available space |
| Constraint enforcement | Rule-based | Object positions, sizes |
| Gestalt grouping | Heuristic | Semantic group membership |

### Design Constants

- **Target fill:** 67% content, 33% breathing room
- **Edge margin:** 2% from all edges
- **Minimum gap:** 3% between any two blocks
- **Golden ratio (PHI):** 1.618033988749895
- **All sizes relative** to full canvas (0.0–1.0 fractions, converted to pixels only at render time)

### Typography Hierarchy (Golden Ratio)

Font sizes scale by PHI:
- Body: base size
- Subheading: base × 1.618
- Heading: base × 1.618²
- Display: base × 1.618³

### Interactive Simulator for Training

Build an HTML/CSS interactive simulator to collect human ratings:
- Shows layout variants with real content from trace data
- "Good" / "Bad" buttons to rate each layout
- Captures all layout attributes + rating to JSON
- Use collected data to refine heuristic thresholds
- Keyboard shortcuts for rapid iteration (R=refresh, G=good, B=bad)

### Gestalt Principles to Apply

- **Proximity:** objects in the same semantic group are placed closer
- **Similarity:** objects with the same function look the same (same shape, similar color)
- **Continuity:** reading flow follows a natural path (top-left to bottom-right)
- **Closure:** grouped elements feel like a complete unit

### Implementation Notes

- Start with the simulator to validate the algorithm visually
- Collect 50+ good/bad ratings to establish baseline thresholds
- The Object Builder is where most intelligence lives (grouping, importance, styling)
- The Object Placer is mostly geometric constraint solving
- Agent can be used for heuristic decisions when calculation is not possible,
  using information available from other agents and metadata
