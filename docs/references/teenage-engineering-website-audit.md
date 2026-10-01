# Teenage Engineering website reference audit

**Purpose:** Design research for a future OceanEdge Technologies company website. KaazDaak is one OceanEdge product and should appear within the company site's product section.

**Reference:** [teenage.engineering](https://teenage.engineering/)  
**Product page inspected:** [EP–133 K.O. II](https://teenage.engineering/products/ep-133)  
**Reviewed:** 1 October 2026  
**Scope:** Visual inspection of the homepage and EP–133 product page, plus read-only inspection of rendered DOM/CSS on the product page. This is a design audit, not an exhaustive crawl of every route or a copy of the site's source/assets.

## Overall visual character

- Strong editorial art direction: the page feels like a product catalogue, design journal, and shop combined.
- Graphic identity is intentionally unusual and highly recognizable. The product and its visual world lead; conventional SaaS illustrations and gradient effects are not the focus.
- Mostly monochrome black and white, with product imagery and occasional small accent colors (including orange/red in campaign artwork).
- Large unhurried image areas are contrasted with compact labels, technical details, and dense navigation.
- The design has a playful, handmade/industrial personality while retaining precise alignment and hierarchy.

## Typography

### Observed hierarchy and treatment

- **Wordmark/navigation:** Small lowercase wordmark and compact labels. Navigation categories are paired with simple, distinctive line icons and brief secondary labels.
- **Campaign/display type:** Very large, bold, condensed or tightly set uppercase lettering is used for campaign headlines. The homepage campaign observed during review used an oversized headline above illustrated artwork.
- **Product hero type:** A very large, thin outlined product/model name sits over the hero photograph, with small supporting product descriptors nearby.
- **Body copy:** Lowercase prose is common. Copy is short, direct, and broken into small blocks rather than long marketing paragraphs.
- **Technical labels:** Small uppercase captions, specs, model names, and component labels create a hardware/manual feel.
- **Emphasis:** Scale and weight do most of the work. The type system uses strong differences between display titles, explanatory text, labels, and specifications.

### What is not confirmed

The exact typeface names and licensing were not established by visual inspection. Do not assume a commercial face is freely reusable. Identify and license a suitable typeface independently; test that it includes the Latin and Bangla glyphs needed by OceanEdge.

## Layout and composition

- **Global navigation:** A persistent, wide top navigation band with several compact illustrated/icon-led destinations. Supporting labels are deliberately small. The header adapts visually to different page backgrounds through color/opacity changes.
- **Homepage:** A catalogue-like sequence of product/campaign blocks rather than a conventional startup hero followed by a standard features/pricing template. Product families have strong visual presence and concise labels.
- **Product hero:** Full-bleed image-led opening. The model name and supporting product details overlay the image, keeping the product as the central visual anchor.
- **Long-form product storytelling:** A single vertical page alternates product imagery/video, concise descriptions, feature lists, interactive/slider content, technical diagrams, accessories, and specifications.
- **Horizontal ticker:** A narrow, high-contrast announcement/purchase strip repeats its message across the viewport.
- **Product information:** Specifications and feature details are separated into clear groups and lower-priority sections, so the editorial opening stays visually dominant.
- **Whitespace:** Broad areas of whitespace (or dark image fields) separate sections; dense detail is grouped into defined modules.
- **Responsive assets:** The inspected product route used responsive image sources at multiple sizes rather than one fixed-size image for every screen.

## Motion and interaction inventory

These are the motion patterns observed or identified in rendered CSS on the inspected routes. They are descriptions, not extracted copies of Teenage Engineering source code.

| Pattern | Observed behavior / implementation clue | Design role |
|---|---|---|
| Repeating announcement ticker | A track translates horizontally in a repeating CSS keyframe animation. The stylesheet includes a `prefers-reduced-motion` rule that pauses it. | Adds energy and makes a short announcement persistent without taking a large area. |
| Horizontal content slider | Slider panels move by changing their horizontal position, with duration controlled through a CSS custom property. | Lets a long product story remain visually compact and interactive. |
| Header theme transition | Navigation icon/text colors and selected outlines transition between page color themes. A shared theme-duration variable controls timing. | Keeps the dense icon header legible across changing hero backgrounds. |
| Cart feedback | The cart/bag icon briefly scales up and returns to its base size (CSS keyframe called `bulge`, about 250 ms). | Confirms a small purchase action without a large modal or interruption. |
| Add-to-cart feedback | Add icon transitions in scale/opacity; hover and added states use different scales and colors. | Gives immediate, localized response to an action. |
| Product video | The EP–133 page contains video elements with looped WebM/MP4 sources, including product demonstration content. Video controls fade with player state. | Shows the object and its operation in motion instead of relying only on static renders. |
| Background movement | Stylesheets expose `backgroundScroll` and `desktop-backgroundScroll` keyframes. | Provides ambient motion for selected visual treatments; not a universal page effect. |
| Loading feedback | A rotating CSS spinner is present in the shared styles. | Covers waiting states rather than serving as decorative hero motion. |
| Product imagery/overlays | The product page layers type and small annotations over large editorial images. Visual inspection does not establish that every overlay animates on scroll. | Makes product imagery carry both brand and explanatory content. |

### Motion implementation signals observed

- Rendered CSS uses keyframes, transitions, CSS custom properties, and responsive media rules.
- The inspected product page had video elements and video-player styling; no canvas animation was found in that page state.
- The marquee has an explicit reduced-motion accommodation. Keep that behavior in any future implementation.
- Do not infer a particular animation framework (such as GSAP) from appearance alone. No named animation framework was confirmed in this inspection.

## Interaction details worth noting

- Use a very small number of clear destinations in the global navigation, but make each destination feel like part of the brand rather than default text links.
- Keep feedback near the control that changed (cart/add action) instead of relying on large generic confirmation overlays.
- Use repeated ticker copy only for genuinely useful messages; duplicate text should remain understandable to assistive technology.
- Product storytelling can use video/slider modules, but core descriptions and calls to action should remain usable when motion is disabled or media does not load.

## OceanEdge adaptation notes

Use this as a reference for a **similar level of craft and expressive restraint**, not as a requirement to reuse Teenage Engineering's exact page, logo, fonts, artwork, copy, or assets.

- Keep OceanEdge as the parent company brand in the masthead, introduction, and footer.
- Place KaazDaak in a clearly named **Products** section and present it as one product made by OceanEdge.
- Translate the reference's product-catalogue clarity into OceanEdge's actual work: what the company builds, who it serves, and how to learn more.
- Establish an original OceanEdge visual system first: wordmark, typefaces, colors, icon language, and original imagery.
- Use display typography for the company statement, compact labels for navigation/metadata, and readable body type for explanations. Confirm Bangla and English glyph coverage if both languages are planned.
- Choose motion by purpose: one ticker, small hover/press feedback, selected reveal transitions, and product demo media. Keep timing consistent and provide reduced-motion behavior.
- Avoid adding animation to every element. The reference's identity comes from its art direction and layout as much as motion.

## Public reference routes

- [Homepage](https://teenage.engineering/)
- [Products index](https://teenage.engineering/products)
- [EP–133 K.O. II product page](https://teenage.engineering/products/ep-133)
- [Designs section](https://teenage.engineering/designs)
- [Latest/news section](https://teenage.engineering/now)

The site's original page code, media, logo, illustrations, and type assets remain the property of their respective rights holders. This document records observations and links to the public references; it does not package or redistribute those files.
