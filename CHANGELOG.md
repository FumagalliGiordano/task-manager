# CHANGELOG

## [v2.0.0] - 2026-03-19

### Fix (QA Report)

#### Bug risolti
- **[BUG-1] Race condition caricamento dati**
  - `TaskService` non mantiene più stato in memoria (`self._tasks`)
  - Ogni operazione di scrittura esegue un reload da disco prima di agire
  - File locking via `filelock` (cross-platform) durante ogni accesso al file

- **[BUG-2] ID non univoci in scenari multi-istanza**
  - `_next_id()` ora riceve il dataset appena letto da disco
  - Il calcolo dell'ID avviene sempre sullo stato più aggiornato disponibile

- **[BUG-3] Scrittura non atomica**
  - Implementata strategia **write-to-temp-then-rename**
  - Il file `tasks.json` non viene mai lasciato in stato parziale/corrotto
  - In caso di crash durante la scrittura, il file originale rimane intatto

#### Edge case risolti
- **Titoli con soli spazi**: validator Pydantic `@field_validator` rifiuta
  stringhe blank e normalizza (strip) il titolo in ingresso
- **File storage corrotto**: invece di fallire silenziosamente e sovrascrivere,
  ora viene creato un backup `.json.bak` e sollevata una `RuntimeError` esplicita
- **Errori di validazione in CLI**: la CLI cattura `ValidationError` Pydantic
  e mostra un messaggio leggibile all'utente prima di uscire con codice 1

### Test case coperti
| ID    | Scenario                        | Stato    |
|-------|---------------------------------|----------|
| TC-01 | Titolo vuoto                    | ✅ Fix   |
| TC-02 | Completamento task inesistente  | ✅ OK    |
| TC-03 | Caratteri speciali UTF-8        | ✅ OK    |
| TC-04 | Delete con annullamento         | ✅ OK    |
| TC-05 | Concorrenza (simulazione)       | ✅ Fix   |

## [v1.0.0] - 2026-03-19
- Release iniziale
