# Configuration

## Locations

| Kind | Path |
|------|------|
| User config | `$XDG_CONFIG_HOME/m3utolocal/config.json` |
| System | `/usr/local/etc/cloudbsd/m3utolocal/config.json` |
| Library (downloads) | `$XDG_DATA_HOME/m3utolocal/library/` (or `-o`) |

## Generate

```bash
m3utolocal init
```

## Keys

```json
{
  "language": "en",
  "m3u_path": "chans.m3u",
  "output_dir": "",
  "threads": 1,
  "retries": 1,
  "auto_clean_parts": false,
  "log_level": "INFO",
  "theme": "default"
}
```

Precedence: CLI → env (`M3UTOLOCAL_*`) → user config → system → defaults.
