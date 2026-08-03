# Template — `less/theme.<slug>.less` (YOOtheme child style)

Copy into `<child-theme>/less/theme.<slug>.less`. Replace `<slug>`, `<Name>` and
the `@prj-` prefix with the project's own. See `references/yootheme-less.md` for
the mechanics behind every marked trap.

**Fill section 1 with real values before mapping section 2.** Mapping placeholder
tokens onto UIkit ships a look nobody chose.

````less
/*

Name: <Name>
Background: Light
Color: <Colour>
Type: Flat

*/

// ========================================================================
// <Name> — YOOtheme style
//
// Maps the <Name> design system onto YOOtheme / UIkit theme variables, so
// every element built in the YOOtheme builder inherits the correct font,
// colour, spacing and radius automatically.
//
// Select it in: Customizer → Theme → Style → "<Name>".
//
// SOURCE OF TRUTH for section 1 is <the design file / tokens.css / Figma URL>.
//
// ⚠ THIS FILE IS THE SOURCE OF TRUTH FOR THE TOKENS — NOT THE CUSTOMIZER.
// The Customizer exposes variables by PATTERN whitelist (config/styler.php), so
// the two halves of this file behave DIFFERENTLY there:
//   - section 2's mappings (@global-*, @base-*, @button-*, @card-*, @navbar-*,
//     @inverse-*) DO appear as editable fields;
//   - section 1's @prj-* tokens match no pattern and never appear.
// Editing a colour under Customizer → Global → Colors overrides the MAPPED
// value while the token it derived FROM still reads the old one. They diverge
// silently, the DB copy wins at runtime, and this file goes stale.
// So: change brand values HERE. Use the Customizer for fonts and per-page work.
// ========================================================================

// NOTE: this style lives in the CHILD theme. YOOtheme discovers it by globbing
// {rootDir,childDir}/less/theme.*.less (packages/styler/src/Styler.php), and
// resolves @import paths relative to THIS file — so each import below reaches
// the parent via ../../<parent>/…
@import "../../<parent>/less/platform.less";
@import "../../<parent>/vendor/assets/uikit/src/less/uikit.less";
@import "../../<parent>/vendor/assets/uikit-themes/master/_import.less";
@import "../../<parent>/less/theme.less";


// ========================================================================
// 1. <NAME> TOKENS — quote the design-tool variable beside each value, so a
//    future session can diff against the source without guessing.
// ========================================================================

// ---------- Palette ----------
@prj-ink:            #000000;   // design: <token name>
@prj-primary:        #000000;   // design: <token name>
@prj-accent:         #000000;   // design: <token name>
@prj-bg:             #ffffff;   // design: <token name>
@prj-bg-alt:         #ffffff;
@prj-line:           #e5e5e5;
@prj-text:           @prj-ink;
@prj-text-muted:     #666666;

// Derived states. NOTE: a near-black brand colour darkens poorly — on such a
// palette, hover should LIGHTEN instead.
@prj-primary-hover:  darken(@prj-primary, 8%);

// ---------- Typography ----------
// The FILES are loaded via Customizer → Theme → Style → Fonts (YOOtheme
// self-hosts them). These stacks only NAME the families + fallbacks.
// ⚠ A design tool may report optical-size CUTS as families ("Inter 18pt",
// "Fraunces 72pt SuperSoft"). The CSS family name is the plain one.
@prj-font-body:      "<Body>", system-ui, -apple-system, sans-serif;
@prj-font-display:   "<Display>", Georgia, serif;

// Desktop values. If the design ships no mobile scale, do NOT invent one —
// treat these as the large-screen end and let UIkit's `-m` variables handle
// smaller screens (section 2).
@prj-t-h1:           0px;   // design: <token>
@prj-t-h2:           0px;
@prj-t-h3:           0px;
@prj-t-h4:           0px;
@prj-t-body:         16px;

@prj-lh-tight:       1.1;
@prj-lh-body:        1.5;

// ---------- Spacing / radii / shadows ----------
@prj-s-1:  4px;  @prj-s-2:  8px;  @prj-s-3: 12px;  @prj-s-4: 16px;
@prj-s-6: 24px;  @prj-s-8: 32px;  @prj-s-12: 48px; @prj-s-16: 64px;

@prj-r-sm: 4px;  @prj-r-md: 8px;  @prj-r-lg: 16px; @prj-r-pill: 999px;

// Wrap in ~"..." so LESS emits them verbatim. Tinting with the brand colour
// instead of pure black keeps elevation on-brand.
@prj-shadow-sm: ~"0 1px 2px rgba(0, 0, 0, 0.05)";
@prj-shadow-md: ~"0 4px 12px -2px rgba(0, 0, 0, 0.08)";

// ---------- Layout ----------
@prj-content-max: 1280px;
@prj-gutter:      @prj-s-8;


// ========================================================================
// 2. MAP ONTO YOOtheme / UIkit VARIABLES
//    This is the half that does the work — section 1 alone changes nothing.
//    ⚠ VERIFY every name against the install before using it:
//      grep -rn "^@button-primary-background:" \
//        ../../<parent>/vendor/assets/uikit/src/less/components/button.less
// ========================================================================

// ---------- Global ----------
@global-color:                @prj-text;
@global-emphasis-color:       @prj-ink;
@global-muted-color:          @prj-text-muted;
@global-inverse-color:        @prj-bg;
@global-background:           @prj-bg;
@global-muted-background:     @prj-bg-alt;
@global-primary-background:   @prj-primary;
@global-secondary-background: @prj-accent;
@global-border:               @prj-line;
@global-border-width:         1px;
@global-link-color:           @prj-accent;

@global-font-family:          @prj-font-body;
@global-font-size:            @prj-t-body;
@global-line-height:          @prj-lh-body;
@global-small-font-size:      14px;
@global-medium-font-size:     @prj-t-h4;
@global-large-font-size:      @prj-t-h3;
@global-xlarge-font-size:     @prj-t-h2;
@global-2xlarge-font-size:    @prj-t-h1;

@global-margin:               @prj-s-6;
@global-small-margin:         @prj-s-2;
@global-medium-margin:        @prj-s-8;
@global-large-margin:         @prj-s-16;
@global-gutter:               @prj-gutter;
@global-control-height:       48px;

// ---------- Base + headings ----------
// UIkit's `-m` pattern gives responsive headings for free: `-m` is the desktop
// value, the bare one is for smaller screens (UIkit's default is `-m * 0.85`).
@base-body-background:        @prj-bg;
@base-body-font-family:       @prj-font-body;
@base-heading-font-family:    @prj-font-display;
@base-heading-color:          @prj-ink;
@base-heading-text-transform: none;

@base-h1-font-size-m:         @prj-t-h1;
@base-h1-font-size:           @prj-t-h1 * 0.6;
@base-h1-line-height:         @prj-lh-tight;
@base-h2-font-size-m:         @prj-t-h2;
@base-h2-font-size:           @prj-t-h2 * 0.65;
@base-h3-font-size:           @prj-t-h3;
@base-h4-font-size:           @prj-t-h4;

// UIkit exposes no per-heading letter-spacing/weight variable, so these are
// the rare RULES (not assignments) that belong here. Delete if not needed.
// h1, .uk-h1 { font-weight: 300; letter-spacing: -0.03em; }

// ---------- Buttons ----------
// ⚠ The master theme forces uppercase + a small font size. Override if the
// design says otherwise.
@button-text-transform:             none;
@button-font-size:                  @prj-t-body;
@button-line-height:                @global-control-height;
@button-padding-horizontal:         @prj-s-8;
@button-primary-background:         @prj-primary;
@button-primary-color:              @prj-bg;
@button-primary-hover-background:   @prj-primary-hover;
@button-default-background:         transparent;
@button-default-color:              @prj-ink;
@button-default-border:             @prj-ink;
@button-default-hover-background:   @prj-ink;
@button-default-hover-color:        @prj-bg;

// UIkit has no global button-radius variable.
.uk-button { border-radius: @prj-r-md; }

// ---------- Cards / forms / navbar / containers ----------
@card-default-background:      @prj-bg-alt;
@card-body-padding-horizontal: @prj-s-8;
@card-body-padding-vertical:   @prj-s-8;

@form-background:              @prj-bg-alt;
@form-border:                  @prj-line;
@form-focus-border:            @prj-primary;
@form-height:                  @global-control-height;

@navbar-background:                transparent;
@navbar-nav-item-font-size:        @prj-t-body;
@navbar-nav-item-text-transform:   none;
@navbar-nav-item-color:            @prj-ink;
@navbar-nav-item-hover-color:      @prj-accent;

@container-max-width:          @prj-content-max;

// ---------- Inverse (dark sections) ----------
// Drives every element inside a section set to a dark background.
@inverse-global-color:            fade(@prj-bg, 80%);
@inverse-global-emphasis-color:   @prj-bg;
@inverse-global-muted-color:      fade(@prj-bg, 60%);
@inverse-global-inverse-color:    @prj-ink;
@inverse-global-border:           fade(@prj-bg, 20%);
@inverse-base-heading-color:      @prj-bg;


// ========================================================================
// 3. EMIT CUSTOM PROPERTIES (optional but recommended)
//    LESS variables are compile-time only. Re-emitting them lets builder
//    Custom CSS, page JS and later section work share one vocabulary.
// ========================================================================

:root {
    --prj-ink:          @prj-ink;
    --prj-primary:      @prj-primary;
    --prj-accent:       @prj-accent;
    --prj-bg:           @prj-bg;
    --prj-text:         @prj-text;
    --prj-text-muted:   @prj-text-muted;
    --prj-line:         @prj-line;
    --prj-font-body:    @prj-font-body;
    --prj-font-display: @prj-font-display;
    --prj-s-4:          @prj-s-4;
    --prj-s-8:          @prj-s-8;
    --prj-r-md:         @prj-r-md;
    --prj-shadow-md:    @prj-shadow-md;
    --prj-content-max:  @prj-content-max;
}
````

## Verify before calling it done

```bash
# 1. It COMPILES (discoverable ≠ compiles). Mind SIGPIPE — don't pipe to head.
cd <scratchpad> && npm install less@4 --no-save
cd <theme>/less && <scratchpad>/node_modules/.bin/lessc --no-color \
  theme.<slug>.less "<scratchpad>/out.css" 2>"<scratchpad>/err.txt"; echo "EXIT:$?"

# 2. Real errors only (the rest is YOOtheme's own vendor noise)
grep -vE "WARNING|complex selectors|Skipped data-uri|^\s*$" "<scratchpad>/err.txt"

# 3. YOOtheme sees the right id + name
ddev wp eval '$s=\YOOtheme\Application::getInstance()->get(\YOOtheme\Theme\Styler\Styler::class);
foreach($s->getThemes() as $t) printf("id=%s name=%s\n",$t["id"],$t["name"]);'

# 4. Then SELECT it in Customizer → Theme → Style and look at it.
#    Compiling is not the same as looking right.
```
