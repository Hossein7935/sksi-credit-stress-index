# SKSI — Synchronisierter Kreditstress-Index

https://hossein7935.github.io/sksi-credit-stress-index/

Wöchentlicher Index dafür, ob Angst vor Unternehmensausfällen gerade ein Einzelfall ist oder auf solide Firmen und die Finanzierung übergreift.

Stand **2. Oktober 2026: 17 / 100, ruhig.** High-Yield-OAS, Investment-Grade-OAS und die Ausfallprämie liegen unter ihrem normalen Niveau. Kein Quorum.

Kein Handelssignal und keine Anlageberatung. Der Index sagt, ob Kreditstress *jetzt* breit ist. Er sagt nicht, wann die nächste Krise beginnt.

## Die vier Bausteine

| Baustein | Reihe | Was ein Anstieg bedeutet |
|---|---|---|
| High-Yield-OAS | FRED `BAMLH0A0HYM2` | Mehr Angst vor Ausfällen schwacher Firmen |
| Investment-Grade-OAS | FRED `BAMLC0A0CM` | Der Stress greift auf solide Firmen über |
| Ausfallprämie | FRED `DBAA` minus `DAAA` | Höherer Preis für Ausfallrisiko |
| NFCI | FRED `NFCI` | Finanzierung wird insgesamt enger |

### Warum keine CDS-Par-Spreads

CDX-Spreads (die gehandelten CDS-Indizes) gehören S&P Dow Jones. Es gibt keine freie API, die ihre Historie jede Woche nachliefert, und die Rohreihe darf hier nicht nachgebaut werden. Auf dem Wochentakt des NFCI laufen CDX und die Cash-Spreads ohnehin fast gleich.

Die vierte Reihe ist deshalb die öffentliche Ausfallprämie von Moody’s: Rendite Baa minus Aaa. Sie misst genau das, was die CDS-Zeile meint — wie viel Extra der Markt für Ausfallrisiko verlangt — und sie aktualisiert sich täglich über FRED. Sie ist ein eigener Markt (Moody’s-Anleihen), nicht eine Kopie des ICE-OAS.

## Rechnung

Normalniveau und Skala sind **eingefroren auf 1997–2006**, also vor der Finanzkrise. Neue Wochen verschieben die Vergangenheit nicht.

Für jeden Baustein:

```
z = (heutiger Wert − Median 1997–2006) / robuste Skala
```

Daraus:

```
Lage   = 0,30·z(HY) + 0,25·z(IG) + 0,25·z(Ausfallprämie) + 0,20·z(NFCI)
Quorum-Term = der schwächste der vier z-Werte, aber nur wenn er positiv ist
Tempo  = durchschnittlicher Anstieg der z-Werte über vier Wochen, negative Änderungen zählen nicht
Rohwert = 0,70·Lage + 0,20·Quorum-Term + 0,10·Tempo
```

Der schwächste Baustein bremst den Index. Ein einzelner Ausreißer, etwa nur High Yield, kann nicht allein „alle Signale“ auslösen.

Der Rohwert wird auf 0–100 gezeichnet. Die Schwellen sind die Perzentile des Rohwerts **im selben Fenster 1997–2006** und wurden danach nicht mehr angefasst:

| Score | Lage | Bedeutung |
|---|---|---|
| unter 48 | normal | ruhig |
| 48–68 | watch | erhöht |
| 68–84 | stress | deutlicher Kreditstress |
| ab 84 | severe | schwer |
| Quorum | alle vier z > 0,75 und mindestens Stress | die eigentliche Warnung: alles gleichzeitig |

## Hat das historisch funktioniert?

Geprüft als Warnsystem, nicht als Handelssystem. Die Schwellen standen fest, bevor 2008, 2011, 2016 und 2020 bewertet wurden.

| Episode | Ergebnis |
|---|---|
| LTCM, Aug–Nov 1998 | Kein Alarm (Spitze 46). Der NFCI war eng, die Ausfallprämie nicht. Das war ein Liquiditätsereignis, und es liegt im Kalibrierungsfenster. |
| Enron/WorldCom 2002 | Schwer, Spitze 86. Quorum in einem Teil der Wochen. |
| Vor Lehman | 9. Nov 2007 erhöht, 23. Nov 2007 Stress, 11. Jan 2008 schwer. Lehman war der 15. Sep 2008. |
| Sep 2008–Sep 2009 | Quorum in jeder Woche, 98 % der Wochen schwer, Spitze 100. |
| Euro-Schulden, 2. Halbjahr 2011 | Schwer, Spitze 86, Quorum. |
| Energie/High-Yield, Winter 2015/16 | Stress, Spitze 82, Quorum, aber nicht schwer. Sektorstress, keine Systemkrise. |
| COVID, März 2020 | 6. März noch knapp ruhig, 13. März schwer (94). Der Index lief mit dem Kreditmarkt, er hat die Pandemie nicht vorhergesehen. |
| Zinsjahr 2022 | Höchstens erhöht (Spitze 56). Nie Stress. Richtig: teurere Zinsen, keine Pleitewelle. |
| SVB, März 2023 | Erhöht (Spitze 52), ein paar Wochen, kein Quorum. |
| Ruhige Strecken 2004–06, 2013–14, 2017–19, Mai 2023–Jul 2024 | Keine einzige Woche über 48. |

Nicht perfekt. Perfekt gibt es bei Kreditstress nicht. Für die Frage „ist das breit und ernst?“ hat die Regel die großen Episoden nach 2006 getroffen und die ruhigen Jahre in Ruhe gelassen.

## Aktualisierung

Ein GitHub-Action läuft werktags um 21:15 UTC, zieht die fünf FRED-Reihen ohne API-Key und schreibt `data/sksi_weekly.csv`, `data/latest.json` und `docs/history.svg` neu, wenn sich etwas geändert hat.

Seit April 2026 liefert FRED von den ICE-Spreads nur noch ein rollierendes Fenster von etwa drei Jahren. Der Action braucht nur den aktuellen Rand. Die ältere Index-Historie bleibt stehen und wird nicht aus diesem Fenster neu erfunden. NFCI, DBAA und DAAA kommen weiterhin in voller Länge.

Lokal:

```bash
python -m sksi          # letzten gespeicherten Stand zeigen
python -m sksi.update   # von FRED neu rechnen
python -m unittest discover -s tests
```

Nur die Standardbibliothek. Kein API-Key.

## Dateien

- [sksi/model.py](sksi/model.py) — Formel
- [sksi/calibration.json](sksi/calibration.json) — eingefrorene Mediane, Skalen, Schwellen
- [data/sksi_weekly.csv](data/sksi_weekly.csv) — Wochenwerte seit 1997
- [data/latest.json](data/latest.json) — aktueller Stand mit den vier Bausteinen
- [docs/history.svg](docs/history.svg) — Verlauf

Die ICE-Rohreihen sind nicht im Repository. Veröffentlicht ist nur der daraus gerechnete Index.

## Quellen

ICE BofA OAS über FRED (`BAMLH0A0HYM2`, `BAMLC0A0CM`), Moody’s Seasoned Corporate Bond Yields über FRED (`DBAA`, `DAAA`), Chicago Fed National Financial Conditions Index über FRED (`NFCI`).
