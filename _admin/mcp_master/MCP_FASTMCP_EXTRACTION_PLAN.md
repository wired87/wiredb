# MCP FastMCP Auto-Extraction Prompt + Plan

## Verbesserter Prompt (Best Practice)

Du bist ein Python-Architekt mit Fokus auf `mcp` (Python SDK) und `FastMCP`.

Ziel:
- Implementiere in `mcp_master` eine automatische Tool-Registrierung fuer Klassen, deren Name `MCP` enthaelt.
- Beruecksichtige nur Klassen, deren Name **nicht** mit `_` beginnt.
- Beruecksichtige in diesen Klassen nur Methoden, deren Name **nicht** mit `_` beginnt.
- Exponiere alle gefundenen Methoden als FastMCP-Tools.

Funktionale Anforderungen:
1. Discovery:
   - Scanne programmatisch alle relevanten Module unter `mcp_master`.
   - Finde Klassen mit `MCP` im Namen (Case-sensitive), die nicht mit `_` starten.
   - Finde oeffentliche Methoden dieser Klassen (ohne `_`-Prefix).
2. Extraktion:
   - Nutze primaer eingebaute Introspection (`inspect`, `typing.get_type_hints`, Signaturen/Annotations).
   - Falls noetig, nutze/erweitere `StructInspector` fuer AST-basierte Analyse.
   - Erweitere `StructInspector`, damit auch Methoden-Kommentare/Docstrings (inkl. Inline-Kommentare im Methodenkoerper, soweit AST-seitig sinnvoll) als Metadaten erfasst werden.
3. Input-Schema:
   - Leite fuer jede extrahierte Methode ein Input-Struct (JSON-Schema/Pydantic-kompatibel) aus Signatur + Typannotationen + Defaults ab.
   - Falls Typannotationen fehlen, markiere Felder klar als `Any` und fuege Warnhinweis in die Tool-Beschreibung ein.
4. FastMCP Exposure:
   - Registriere jedes Tool mit `@server.tool(...)` oder aequivalenter dynamischer Tool-Registrierung.
   - Setze pro Tool:
     - stabilen `name`,
     - klare `description` (aus Docstring/Kommentar + Fallback),
     - sinnvolle `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
5. Robustheit:
   - Fehlerhafte Klassen/Methoden duerfen den Discovery-Prozess nicht abbrechen.
   - Logge pro uebersprungener Methode den Grund.
6. Tests:
   - Tests fuer Discovery-Filter (`MCP` im Klassennamen, Ausschluss `_`).
   - Tests fuer Schema-Ableitung.
   - Tests fuer erfolgreiche Registrierung in `list_tools`.

Technische Leitlinien (MCP Python Best Practices):
- Nutze starke Typisierung statt unnoetigem `Dict[str, Any]`.
- Halte Tool-Namen stabil und rueckwaertskompatibel.
- Beschreibungen muessen handlungsorientiert sein (wann/warum Tool verwenden).
- Trenne Discovery, Schema-Building und Registration in eigene Komponenten.
- Liefere deterministic output (gleiche Reihenfolge bei gleicher Codebasis).

Erwartetes Ergebnis:
- Eine lauffaehige FastMCP-Server-Integration in `mcp_master`, die die beschriebenen Methoden automatisch als Tools veroeffentlicht.
- Dokumentation der Mapping-Regeln (Klasse/Methodenname -> Toolname, Input-Schema, Beschreibungsquelle).


## Umsetzungsplan in `mcp_master`

1. **Discovery-Layer erstellen**
   - Neue Komponente, z. B. `mcp_master/mcp_server/auto_discovery.py`.
   - Modulscan + Klassenfilter (`"MCP" in class_name`, `not class_name.startswith("_")`).
   - Methodenfilter (`callable`, `not method_name.startswith("_")`).

2. **StructInspector erweitern**
   - Bestehenden `StructInspector` um Methoden-Metadaten erweitern:
     - Docstring,
     - Inline-Kommentar-Hinweise aus AST (falls vorhanden),
     - Signatur-Details (Typen, Defaults, required/optional).
   - Rueckgabe als strukturierte Datenklasse statt losem Dict.

3. **Schema-Building implementieren**
   - `method -> input schema` Builder (Pydantic/JSON-Schema-kompatibel).
   - Normalisierung fuer `Optional`, `Union`, `List`, `Dict`, `Literal`.
   - Fallback fuer unannotierte Parameter mit klarer Kennzeichnung.

4. **Tool-Registration kapseln**
   - Neue Komponente, z. B. `mcp_master/mcp_server/auto_register.py`.
   - Dynamische Registrierung auf einem `FastMCP`-Server.
   - Tool-Metadaten aus Discovery + Inspector zusammenfuehren.

5. **Integration in Server-Bootstrap**
   - In `mcp_master/mcp_server/main.py` beim Start:
     - Basis-Server initialisieren,
     - Auto-Discovery ausfuehren,
     - Tools registrieren,
     - Ergebnis loggen (`N tools registered`).

6. **Qualitaetssicherung**
   - Unit-Tests fuer Discovery, Schema-Ableitung, Kommentar-Extraktion.
   - Integrationstest: `list_tools` enthaelt auto-registrierte Tools.
   - Negativtest: Klassen/Methoden mit `_` werden nicht registriert.

7. **Dokumentation**
   - README-Abschnitt in `_admin/mcp_master/README.md`:
     - Discovery-Regeln,
     - Namenskonventionen,
     - Grenzen (z. B. fehlende Typannotationen),
     - Beispiel fuer eine registrierte Methode.
