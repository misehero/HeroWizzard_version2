# Frontend Translation Map (EN → CS)

Internal documentation: mapping of database field names to Czech frontend labels,
and all translated UI strings organized by page.

## Database Field → Frontend Label Mapping

### Transaction Model Fields

| DB Field Name          | DB Type    | Frontend Label (CS)   | Notes                              |
|------------------------|------------|-----------------------|------------------------------------|
| `datum`                | DateField  | Datum                 | Bank column, read-only on import   |
| `ucet`                 | CharField  | Účet                  | Bank column                        |
| `castka`               | Decimal    | Částka                | Bank column, displayed with "Kč"   |
| `typ`                  | CharField  | Typ                   | Bank column                        |
| `poznamka_zprava`      | TextField  | Poznámka / Zpráva     | Bank column                        |
| `variabilni_symbol`    | CharField  | Variabilní symbol     | Bank column, abbrev "VS"           |
| `cislo_protiuctu`      | CharField  | Číslo protiúčtu       | Bank column                        |
| `nazev_protiuctu`      | CharField  | Název protistrany     | Bank column                        |
| `nazev_merchanta`      | CharField  | Název obchodníka      | Bank column (Raiffeisen only)      |
| `mesto`                | CharField  | Město                 | Bank column (Raiffeisen only)      |
| `id_transakce`         | CharField  | ID transakce          | Bank column, used for dedup        |
| `status`               | CharField  | Status                | App column                         |
| `prijem_vydaj`         | CharField  | P/V                   | App column: Příjem/Výdaj           |
| `vlastni_nevlastni`    | CharField  | V/N                   | App column: Výnosy/Náklady         |
| `dane`                 | Boolean    | Daně                  | App column, default: checked       |
| `druh`                 | CharField  | Druh (Kategorie)      | App column                         |
| `detail`               | CharField  | Detail                | App column                         |
| `kmen`                 | CharField  | KMEN                  | App column                         |
| `mh_pct`               | Decimal    | MH %                  | App column, KMEN split             |
| `sk_pct`               | Decimal    | ŠK %                  | App column, KMEN split             |
| `xp_pct`               | Decimal    | XP %                  | App column, KMEN split             |
| `fr_pct`               | Decimal    | FR %                  | App column, KMEN split             |
| `projekt`              | FK         | Projekt               | App column                         |
| `produkt`              | FK         | Produkt               | App column                         |
| `podskupina`           | FK         | Podskupina            | App column                         |
| `is_active`            | Boolean    | Aktivní               | Checkbox in table                  |
| `is_deleted`           | Boolean    | (not shown in UI)     | Soft-delete, hidden from user      |

### Transaction Status Choices

| DB Value      | Frontend Label (CS) | Badge Color |
|---------------|---------------------|-------------|
| `importovano` | Importováno         | Blue        |
| `zpracovano`  | Zpracováno          | Yellow      |
| `schvaleno`   | Schváleno           | Green       |
| `upraveno`    | Upraveno            | Gray        |
| `chyba`       | Chyba               | Red         |

### P/V (Příjem/Výdaj) Choices

| DB Value | Frontend Label (CS) | Badge Color |
|----------|---------------------|-------------|
| `P`      | Příjem              | Green       |
| `V`      | Výdaj               | Red         |

### V/N (Výnosy/Náklady) Choices

| DB Value | Frontend Label (CS) | Notes                                |
|----------|---------------------|--------------------------------------|
| `V`      | Výnosy (V)          | Previously "Vlastní" — renamed       |
| `N`      | Náklady (N)         | Previously "Nevlastní" — renamed     |
| `-`      | — (žádné)           | Default / not applicable             |

### KMEN Choices

| DB Value | Frontend Label |
|----------|----------------|
| `MH`     | MH             |
| `SK`     | ŠK             |
| `XP`     | XP             |
| `FR`     | FR             |

### User Role Labels

| DB Value     | Frontend Label (CS) | Badge Color |
|--------------|---------------------|-------------|
| `admin`      | ADMIN               | Red         |
| `manager`    | MANAŽER             | Blue        |
| `accountant` | ÚČETNÍ              | Amber       |
| `viewer`     | ČTENÁŘ              | Gray        |

### Import Batch Status Choices

| DB Value      | Frontend Label (CS) | Badge Color |
|---------------|---------------------|-------------|
| `pending`     | Čekající            | Gray        |
| `processing`  | Zpracovává se       | Yellow      |
| `completed`   | Dokončeno           | Green       |
| `failed`      | Selhalo             | Red         |
| `rolled_back` | Vráceno zpět        | Gray        |

### CategoryRule Match Types

| DB Value    | Frontend Label (CS)        |
|-------------|----------------------------|
| `protiucet` | Protiúčet (Číslo účtu)     |
| `merchant`  | Název obchodníka           |
| `keyword`   | Klíčové slovo              |

### CategoryRule Match Modes

| DB Value   | Frontend Label (CS) |
|------------|---------------------|
| `exact`    | Přesná shoda        |
| `contains` | Obsahuje            |
| `regex`    | Regulární výraz     |

---

## UI Strings by Page

### Navigation (all pages)

| English               | Czech                   |
|-----------------------|-------------------------|
| Dashboard             | Přehled                 |
| Import CSV            | Import CSV              |
| Category Rules        | Pravidla kategorií      |
| Help                  | Nápověda                |
| Logout                | Odhlásit                |
| Loading...            | Načítání...             |

### Login Page (index.html)

| English                        | Czech                            |
|--------------------------------|----------------------------------|
| HeroWizzard - Login            | HeroWizzard - Přihlášení         |
| Financial Management System    | Systém správy financí            |
| Email                          | E-mail                           |
| Password                       | Heslo                            |
| your@email.com                 | vas@email.cz                     |
| Enter your password            | Zadejte heslo                    |
| Sign In                        | Přihlásit se                     |
| Signing in...                  | Přihlašování...                  |

### Dashboard (dashboard.html)

| English                  | Czech                        |
|--------------------------|------------------------------|
| Total Transactions       | Celkem transakcí             |
| Total Income             | Celkové příjmy               |
| Total Expenses           | Celkové výdaje               |
| Uncategorized            | Nezařazené                   |
| Transactions             | Transakce                    |
| Import Backup            | Import zálohy                |
| Export Backup            | Export zálohy                |
| Wipe All                 | Smazat vše                   |
| + Add Transaction        | + Přidat transakci           |
| Export Excel             | Export Excel                 |
| Refresh                  | Obnovit                      |
| Type                     | Typ                          |
| From Date                | Od data                      |
| To Date                  | Do data                      |
| Search                   | Hledat                       |
| Show inactive            | Zobrazit neaktivní           |
| All                      | Vše                          |
| Income (P)               | Příjem (P)                   |
| Expense (V)              | Výdaj (V)                    |
| Date                     | Datum                        |
| Description              | Popis                        |
| Counterparty             | Protistrana                  |
| Amount                   | Částka                       |
| Category                 | Kategorie                    |
| Active                   | Aktivní                      |
| New Transaction          | Nová transakce               |
| Edit Transaction         | Upravit transakci            |
| Basic                    | Základní                     |
| Categorization           | Kategorizace                 |
| KMEN Split               | Rozdělení KMEN               |
| Project / Product        | Projekt / Produkt            |
| Cancel                   | Zrušit                       |
| Save Transaction         | Uložit transakci             |
| Save and open next       | Uložit a otevřít další       |
| Saving...                | Ukládání...                  |
| Previous                 | Předchozí                    |
| Next                     | Další                        |
| Page X of Y (Z total)   | Strana X z Y (celkem Z)      |

### Upload (upload.html)

| English                  | Czech                          |
|--------------------------|--------------------------------|
| Import Bank: Creditas CSV| Import banka: Creditas CSV     |
| Import Bank: Raiffeisen  | Import banka: Raiffeisen CSV   |
| Import format: iDoklad   | Import formát: iDoklad CSV     |
| Click to select          | Klikněte pro výběr             |
| or drag and drop         | nebo přetáhněte soubor         |
| Upload & Import          | Nahrát a importovat            |
| Uploading...             | Nahrávání...                   |
| Total                    | Celkem                         |
| Imported                 | Importováno                    |
| Skipped                  | Přeskočeno                     |
| Errors                   | Chyby                          |
| Import History           | Historie importů               |
| Filename                 | Soubor                         |

### Categories (categories.html)

| English                        | Czech                              |
|--------------------------------|------------------------------------|
| Auto-Categorization Rules      | Pravidla automatické kategorizace  |
| Apply Rules to Uncategorized   | Použít pravidla na nezařazené      |
| + Add Rule                     | + Přidat pravidlo                  |
| Rule Name                      | Název pravidla                     |
| Match Type                     | Typ shody                          |
| Match Mode                     | Režim shody                        |
| Match Value                    | Hodnota shody                      |
| Sets P/V                       | Nastaví P/V                        |
| Sets Category                  | Nastaví kategorii                  |
| Priority                       | Priorita                           |
| Actions                        | Akce                               |
| Edit                           | Upravit                            |
| Delete                         | Smazat                             |
| Exact Match                    | Přesná shoda                       |
| Contains                       | Obsahuje                           |
| Regular Expression             | Regulární výraz                    |
| Case Sensitive                 | Rozlišovat velká/malá písmena      |
| Set P/V                        | Nastavit P/V                       |
| Set V/N                        | Nastavit V/N                       |
| -- Don't set --                | -- Nenastavovat --                 |
| Save Rule                      | Uložit pravidlo                    |
| Description                    | Popis                              |

### Error/Success Messages

| English                                    | Czech                                          |
|--------------------------------------------|-------------------------------------------------|
| Transaction created successfully.          | Transakce úspěšně vytvořena.                    |
| Transaction updated successfully.          | Transakce úspěšně aktualizována.                |
| Date and Amount are required.              | Datum a Částka jsou povinné.                    |
| Negative value is not income.              | Záporná hodnota není příjem.                    |
| Positive value is not expense.             | Kladná hodnota není výdaj.                      |
| Backup exported successfully.              | Záloha úspěšně exportována.                     |
| Import complete: X imported...             | Import dokončen: X importováno...               |
| X transactions soft-deleted.               | X transakcí soft-delete smazáno.                |
| Exported X transactions to Excel.          | Exportováno X transakcí do Excelu.              |
| Please select a CSV file.                  | Prosím vyberte CSV soubor.                      |
| Rule created successfully                  | Pravidlo úspěšně vytvořeno                      |
| Rule updated successfully                  | Pravidlo úspěšně aktualizováno                  |
| Rule deleted successfully                  | Pravidlo úspěšně smazáno                        |
| Rules applied. X categorized.              | Pravidla aplikována. X kategorizováno.          |
| API request failed                         | Požadavek API selhal                            |
| Export failed                              | Export selhal                                   |
| Import failed                              | Import selhal                                   |

---

## Terms Kept Untranslated

| Term      | Reason                                                     |
|-----------|------------------------------------------------------------|
| CSV       | Technical file format abbreviation                         |
| KMEN      | Organization-specific term (Czech origin)                  |
| MH/ŠK/XP/FR | Organization-specific tribe abbreviations               |
| P/V       | Domain abbreviation (Příjem/Výdaj)                         |
| V/N       | Domain abbreviation (Výnosy/Náklady)                       |
| VS        | Standard Czech abbreviation for Variabilní symbol          |
| Excel     | Product name                                               |
| iDoklad   | Product name                                               |
| Creditas  | Bank name                                                  |
| Raiffeisen| Bank name                                                  |
| HeroWizzard | Application name                                         |
| Admin     | Role name (universally understood)                         |
| API       | Technical term                                             |
| JSON      | Technical file format                                      |
| UUID      | Technical identifier format                                |

---

## Changelog

- **2026-02-13**: Initial full Czech translation of frontend (all 6 files)
  - V/N renamed from "Vlastní/Nevlastní" to "Výnosy/Náklady"
  - Daně checkbox default changed to checked
  - P/V validation messages added (client-side)
  - Save button now shows "Uložit a otevřít další" when editing non-last transaction
  - Currency shown as "Kč" via cs-CZ Intl formatter
