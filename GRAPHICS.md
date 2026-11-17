# Country graphics

The sign pages show one PNG per country per pictogram code:

```text
graphics/<country>/<service-category>-<pictogram-category>.png
```

The German stop sign is:

```text
graphics/de/12-112.png
```

`12` is the service category (regulatory). `112` is the pictogram category. The file name uses those two parts with a hyphen. It does not use the five-digit form `12112`.

PNG is the graphic the page displays. An EMF with the same stem is optional; when it is present the page still shows the PNG and links the EMF. SVG and WebP with the same stem are accepted as well.

Use lowercase country codes and lowercase extensions. The site also accepts the same names in uppercase.

## Country codes

These are the ISO 3166-1 alpha-2 codes for the country columns in the Annex I workbook. The United Kingdom column is `gb`. The workbook groups Russia and Belarus in one column; that column uses `ru`, because ISO 3166-1 has no combined code.

| Code | Workbook column | Directory |
| --- | --- | --- |
| `de` | Germany | `graphics/de/` |
| `fr` | France | `graphics/fr/` |
| `gb` | UK | `graphics/gb/` |
| `it` | Italy | `graphics/it/` |
| `es` | Spain | `graphics/es/` |
| `nl` | Netherlands | `graphics/nl/` |
| `be` | Belgium | `graphics/be/` |
| `ch` | Switzerland | `graphics/ch/` |
| `at` | Austria | `graphics/at/` |
| `ie` | Ireland | `graphics/ie/` |
| `pl` | Poland | `graphics/pl/` |
| `se` | Sweden | `graphics/se/` |
| `fi` | Finland | `graphics/fi/` |
| `no` | Norway | `graphics/no/` |
| `gr` | Greece | `graphics/gr/` |
| `cz` | Czech Rep | `graphics/cz/` |
| `sk` | Slovakia | `graphics/sk/` |
| `ru` | Russia & Belarus | `graphics/ru/` |
| `us` | U.S. | `graphics/us/` |
| `kr` | South Korea | `graphics/kr/` |
| `cn` | China | `graphics/cn/` |
| `jp` | Japan | `graphics/jp/` |

The UN / Vienna column is a convention reference such as `B, 2a`, not a graphic, so there is no `un/` directory.

Reserved rows and code ranges do not get graphic files. A request column (`Request by NL`, `Request by AT`, `Request by DE`) is a workbook note, not a file in that country's directory.

Some workbook extracts are a whole spreadsheet cell with the sign in the middle. Those files look tiny on the sign page because the card scales the whole cell. Crop them to the drawing before committing:

```bash
python3 scripts/normalize_graphics.py
```

The command needs Pillow. It leaves a file alone when the drawing already fills the canvas.

Commit the files in `graphics/`. The page generator copies them into the site build. Do not put them under `docs/` yourself.

After adding or removing files, regenerate the pages so the sign pages and the draft comparison pick them up:

```bash
python3 scripts/build_pages.py
```
