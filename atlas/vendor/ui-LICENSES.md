# Локальные ассеты интерфейса atlas

Пути в таблице отсчитываются от `atlas/`. Для офлайн-страницы, открытой по `file://`, ползунку нужны локальные JS и CSS, а значкам — отдельные SVG из `icons/`. CDN, установка пакетов и сетевые запросы для этих ассетов не нужны. Внешние ссылки ниже служат только для проверки происхождения.

## noUiSlider 15.8.1 — MIT

Готовый браузерный ползунок диапазона (UMD) и его штатные стили.

- [Исходный код](https://github.com/leongersen/noUiSlider/tree/d53446cb7e2bc35c0e6a49f259321a423120b0ae) на ревизии `gitHead` пакета. Закреплённые файлы в репозитории: [JS](https://raw.githubusercontent.com/leongersen/noUiSlider/d53446cb7e2bc35c0e6a49f259321a423120b0ae/dist/nouislider.min.js), [CSS](https://raw.githubusercontent.com/leongersen/noUiSlider/d53446cb7e2bc35c0e6a49f259321a423120b0ae/dist/nouislider.min.css).
- [Официальный дистрибутив `nouislider@15.8.1`](https://registry.npmjs.org/nouislider/-/nouislider-15.8.1.tgz): `package/dist/nouislider.min.js` и `package/dist/nouislider.min.css` → `vendor/nouislider/`, без изменений.
- SHA-512 архива проверен по `dist.integrity` из [метаданных npm 15.8.1](https://registry.npmjs.org/nouislider/15.8.1): `sha512-93TweAi8kqntHJSPiSWQ1o/uZ29VWOmal9YKb6KKGGlCkugaNfAupT7o1qTHqdJvNQ7S0su5rO6qRFCjP8fxtw==`.
- MIT © 2019 Léon Gersen: [оригинал](https://raw.githubusercontent.com/leongersen/noUiSlider/d53446cb7e2bc35c0e6a49f259321a423120b0ae/LICENSE.md); `package/LICENSE.md` → [локальная лицензия](nouislider/LICENSE.md).

## Tabler Icons 3.52.0 — MIT

Контурные значки для инструментов, навигации и управления видом. Все 13 SVG взяты из одной опубликованной сборки `@tabler/icons`.

- [Исходные outline SVG](https://github.com/tabler/tabler-icons/tree/4581ad20d8d13e24f6c3be75caaea1c4ad6c4b35/icons/outline) на коммите `4581ad20d8d13e24f6c3be75caaea1c4ad6c4b35` ([тег `v3.52.0`](https://api.github.com/repos/tabler/tabler-icons/git/ref/tags/v3.52.0)).
- [Официальный дистрибутив `@tabler/icons@3.52.0`](https://registry.npmjs.org/@tabler/icons/-/icons-3.52.0.tgz): `package/icons/outline/<имя>.svg` → `icons/<имя>.svg` с теми же именами и байтами.
- SHA-512 архива проверен по `dist.integrity` из [метаданных npm 3.52.0](https://registry.npmjs.org/@tabler%2Ficons/3.52.0): `sha512-dldKlJNfO/gZnGLcIY0X2EFFKIMGwL/rEvTqglvBgAPFiwj9pZOCN5V3Sf0Gyjq6foX4VQmLdOmsS4w5FdWKAw==`.
- MIT © 2020–2026 Paweł Kuna: [оригинал](https://raw.githubusercontent.com/tabler/tabler-icons/4581ad20d8d13e24f6c3be75caaea1c4ad6c4b35/LICENSE); `package/LICENSE` → [локальная лицензия](tabler/LICENSE).

## Проверка байтов

Предоставленные копии JS, CSS и лицензии noUiSlider совпали с файлами npm 15.8.1. Лицензия Tabler совпала с файлом npm 3.52.0, а предоставленные `cube.svg`, `stack-2.svg` и `ruler-measure.svg` — с исходными файлами на коммите тега. Исходная разметка Tabler отличается от разметки в npm; в `atlas/icons/` эти варианты не смешаны.

| Путь от `atlas/` | Байт | SHA-256 установленного файла |
|---|---:|---|
| `vendor/nouislider/nouislider.min.js` | 27743 | `79222927cb7695f403144b58e31da6a7082d82e08d310b0cd776264d311abe7d` |
| `vendor/nouislider/nouislider.min.css` | 4220 | `9dc9155cfd6331d1f5629881ac0bc63928243fa4c1d83b17ce4921b5200be0ae` |
| `vendor/nouislider/LICENSE.md` | 1069 | `0d1fc6e9892bfb1946c780f040578a4d17060182f7721df77b8e068ac19d1ce4` |
| `icons/cube.svg` | 650 | `bd03caa3dbae10588bdca14acc94e430de30d54b9a3eed59be6dc14e4350093d` |
| `icons/stack-2.svg` | 431 | `729d3e264f4e2e9670cd86f4531141baa78eb94e975198228a8167c8a1eb0572` |
| `icons/search.svg` | 409 | `57e054b6c1508be40d5eba1ea434b702f5ff55dca04e28e5e3f22472c2f6176d` |
| `icons/rotate-clockwise.svg` | 389 | `2d76355d5ebb5a44a6c82e56706e2d9ac62dca06f76a4d38689f91641e25134f` |
| `icons/focus-2.svg` | 561 | `273346ebf838f75b31df81ce9d303ee5ef1e8c2f56f1f85cbcd6ef8d6ef8a482` |
| `icons/arrow-left.svg` | 410 | `cca229008bada786cf2f052b5374047478562cb3de0ca1fe7b2a3db61882a2c0` |
| `icons/arrow-up-right.svg` | 393 | `450ff3ea98d6ccad96032d09e89c8d91b0b332e1dcc05e437ae8093916d5e005` |
| `icons/ruler-measure.svg` | 686 | `5908592a6a691268a0a64887884a4be793658a46eacb3d03c7911f7f37338666` |
| `icons/photo.svg` | 562 | `9aa0bd44bef46e1b80445220ea04499ca145fb3339005e13f1da1b17ad8ac159` |
| `icons/chevron-right.svg` | 365 | `0142561fc2fd1b6a18b2cb0c08959b6037643aecf6adc6612aefe16ec4f39f0f` |
| `icons/x.svg` | 378 | `445e1b53563ad7e089f94dee923c2ef3444c63d45294a733687471a76a3c3b8d` |
| `icons/layers-intersect.svg` | 524 | `d5e04801ab417901f74b16e976f3db732d920f4f9f73ebf0ca61643506d127fd` |
| `icons/zoom-scan.svg` | 574 | `569b8484c50c16e521e30a9ad17a15f5b83a5a9615db1bdd52a228deef2d461e` |
| `vendor/tabler/LICENSE` | 1073 | `b740a1d46122672da62833e97f7e7c8a13fa85cbc7445b584b297cc00dde93db` |
