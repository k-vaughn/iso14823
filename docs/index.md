# Registry for ITS Graphics

This is the public register of pictograms in the ISO 14823-1 graphic data dictionary. Each sign has a stable code so intelligent transport systems can name the same sign in any language, and so a message sent in one country can be shown with the sign used in another.

The dictionary is specified by [ISO 14823-1](https://www.iso.org/standard/76963.html), *Intelligent transport systems — Graphic data dictionary — Part 1: Specification*. Annex I of that standard is the example set of signs for the United Nations convention and for selected countries. This site publishes that annex as pages you can search, and it is the copy the maintenance agency updates between editions of the standard.

## How to use this site

Search by a code or by a word. `12-112` and `stop` both lead to the stop sign. `12112`, the same code written as five digits, matches as well.

<form class="find-form" action="find/" method="get">
<label for="home-q">Code or keyword</label>
<input id="home-q" name="q" type="search" placeholder="12-112 or stop" autocomplete="off">
<button class="find-submit" type="submit">Find a sign</button>
</form>

1. Open [Find a sign](find.md), or use the search box in the header.
2. Choose a result. The sign page gives the definition, whether the code is current or deprecated, the year it was registered or retired, the Vienna Convention reference, and any country graphics on file.
3. To scan a whole group, open a service category below. Regulatory signs are category 12, warning signs are category 11, and so on.

A pictogram code is the service category, a hyphen, and the pictogram category. The stop sign is service category 12 and pictogram category 112: [12-112 STOP](signs/12-112.md). A country graphic uses the ISO 3166-1 two-letter code in the file name, so the German rendering is `graphics/de/12-112.png`.

## Service categories

<!-- registry-counts:start -->
<p>668 pictogram codes are in this edition of the workbook: 513 current, 49 deprecated, 105 reserved, and 1 code range.</p>
<div class="cat-grid">
<a class="cat-card" href="categories/11/"><span class="cat-code">11</span><span class="cat-name">Warning</span><span class="cat-count">78 current · 17 deprecated · 27 reserved</span></a>
<a class="cat-card" href="categories/12/"><span class="cat-code">12</span><span class="cat-name">Regulatory</span><span class="cat-count">132 current · 16 deprecated · 32 reserved</span></a>
<a class="cat-card" href="categories/13/"><span class="cat-code">13</span><span class="cat-name">Informative</span><span class="cat-count">180 current · 4 deprecated · 29 reserved · 1 code range</span></a>
<a class="cat-card" href="categories/21/"><span class="cat-code">21</span><span class="cat-name">Public facilities</span><span class="cat-count">40 current · 7 reserved</span></a>
<a class="cat-card" href="categories/31/"><span class="cat-code">31</span><span class="cat-name">Ambient conditions</span><span class="cat-count">6 deprecated · 1 reserved</span></a>
<a class="cat-card" href="categories/32/"><span class="cat-code">32</span><span class="cat-name">Road conditions</span><span class="cat-count">6 deprecated · 1 reserved</span></a>
<a class="cat-card" href="categories/41/"><span class="cat-code">41</span><span class="cat-name">Supplementary panel</span><span class="cat-count">83 current · 8 reserved</span></a>
</div>
<!-- registry-counts:end -->

## The DRAFT watermark {#draft-watermark}

A sign page that has changed since the last full release of this register shows a red **DRAFT** watermark across the page. It is the same stamp the [ISO 24315 vocabulary](https://isotc204.org/iso24315/) uses for a term that has changed since the last approved release. Lists and search results show a Draft chip on those entries. This page stays clear, so the explanation remains readable.

<div class="draft-explain">
<div class="draft-explain-mark" aria-hidden="true">DRAFT</div>
<p>On a changed sign page the word sits across the whole window, in this red type, and the page text stays selectable underneath it.</p>
</div>

Until the maintenance agency publishes a full release, every sign page carries the watermark. The workbook this site was built from is a working-group document, and there is no approved baseline to compare with yet. The first full release becomes that baseline. Afterward, the watermark appears only on sign pages whose entry or country graphic differs from it. A later full release clears the watermark on every page that matches the new baseline.

The version menu on the published site still opens older releases, including pre-releases. A pre-release is a working publication: changed sign pages in it keep the watermark. A full release is the approved snapshot.

## How the register is maintained {#maintenance}

ISO designates a maintenance agency when a standard needs a register that has to change between editions. For the graphic data dictionary, that agency decides which pictogram codes are current, which are deprecated, and which country graphics belong to each code. Decisions are published through this repository. The steps below are the whole path from a proposal to a version on the site.

1. Someone proposes a change: a new code, a deprecation, a corrected definition, or a country graphic. Graphic files use the names in [GRAPHICS.md](https://github.com/k-vaughn/iso14823/blob/main/GRAPHICS.md), for example `graphics/de/12-112.png`.
2. The maintenance agency reviews the proposal. An accepted change is committed here, together with a root [`VERSION`](https://github.com/k-vaughn/iso14823/blob/main/VERSION) file. A registry change sets `version:` to a SemVer greater than every line in [`RELEASES`](https://github.com/k-vaughn/iso14823/blob/main/RELEASES). Work that is still under review uses a pre-release label such as `0.2.0-alpha.1`. Wording changes on pages such as this one keep the current version and add a `doc-only:` date instead.
3. The `validate-version` check compares that `VERSION` file with `RELEASES` on the base branch. It accepts a registry change only when the new version is greater than every release already recorded, and a documentation-only change only when the version is unchanged and the date is not earlier than the latest release date.
4. After the change is merged, the release workflow appends a line to `RELEASES`, tags the commit (`v0.2.0-alpha.1`, or `docs-YYYY-MM-DD` for a documentation-only release), and publishes that tag with [mike](https://zensical.org/docs/setup/versioning/). Each tag stays available in the version selector. The `latest` alias follows the tag that was just published.
5. A full release has no pre-release label. The maintenance agency publishes one when it approves the register as the new baseline. Sign pages that match that baseline lose the DRAFT watermark. Pages that still differ from it keep the watermark until a later full release includes them.

The site is built with [Zensical](https://zensical.org/) from the Markdown in this repository. `scripts/import_annex.py` reads the Annex I workbook into `data/registry.json`. `scripts/build_pages.py` writes a page per code and applies the watermark by comparing each entry with the last full release.

## Status of a code

| Mark | Meaning |
| --- | --- |
| Current (C) | The code is in force. New implementations use current codes. |
| Deprecated (D) | The code remains so that older messages still decode. It is not reused. |
| Reserved | The number is held for a future assignment. |
| Code range | A block of pictogram categories recorded together in the workbook. |

Deprecated codes stay in the register on purpose. A receiver that does not recognise a deprecated code takes no action, and a later edition does not hand that number to a different sign.

## Where the entries come from

The entries were loaded from ISO/TC 204 WG 10 document N1308, the Annex I workbook for ISO 14823-1. Country columns in that workbook are embedded drawings. This site shows a country when a PNG has been added under `graphics/<country>/<code>.png`, or when the workbook has a written note in that column. An empty country list means the file has not been stored yet.

Pictogram codes are also registered on the object-identifier tree under `{joint-iso-itu-t(2) its(28) gdd(5)}`. Version 1 of the dictionary is the country code plus the pictogram code. Version 2 adds a relative object identifier so a more specific sign can still be read as its parent category. This site publishes the Annex I codes and the country graphics; the ASN.1 modules remain in the standard.

[Comment on this page](https://github.com/k-vaughn/iso14823/issues/new?template=page-feedback.yml&title=%5BPage+feedback%5D+Registry+for+ITS+Graphics&page-title=Registry+for+ITS+Graphics&page-path=index.md)
