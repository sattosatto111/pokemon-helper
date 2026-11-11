# 배틀 도감

포켓몬 챔피언스 랭크배틀용 상성·데미지·스피드 계산기 + 실전 메타·인기 파티 도우미야. 1~9세대 규칙도 지원해.
배포: https://sattosatto111.github.io/pokemon-helper/

## 비공식 안내

비공식 팬 사이트야. Pokémon 및 관련 명칭·이미지의 권리는 Nintendo / Creatures Inc. / GAME FREAK inc. / The Pokémon Company에 있어.

## 데이터 출처와 라이선스

- [Pokémon Showdown](https://github.com/smogon/pokemon-showdown) 데이터 (MIT)
- [PokeAPI](https://pokeapi.co) (BSD-3-Clause) / [스프라이트](https://github.com/PokeAPI/sprites)
- [Smogon usage stats](https://www.smogon.com/stats/)
- Battle data provided by Pokémon Champions Battle Data (https://championsbattledata.com)
- [pokedb](https://champs.pokedb.tokyo/) 공개 데이터

Pokémon Showdown 유래 데이터의 MIT 라이선스 고지:

```
The MIT License (MIT)

Copyright (c) 2011-2024 Guangcong Luo and other contributors
http://guangcongluo.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

앱 코드 라이선스 미정.

## 데이터 갱신

GitHub Actions가 주기적으로 갱신해서 커밋해.
- `meta.yml`: 메타(사용률) 데이터
- `teams.yml`: 인기 파티 데이터

## 로컬 실행

빌드 없이 `index.html`을 브라우저로 열면 돼.
