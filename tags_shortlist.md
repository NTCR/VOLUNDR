# Tag vocabulary v1 — review shortlist

Pre-filtered from `tags_frequency.md` (1541 candidates). Method: ranked by
**extractor agreement** (how many of the 4 signals fired), not raw frequency;
LLM-suggested terms weighted as the English spine; id/numeric junk removed;
stemmer variants merged and translated to English canonical.

**How to use this:** skim the KEEP block, delete any you don't want, then paste
the survivors into `_META/tags.yaml` under `approved`. The `aliases` column is
important — it maps the Spanish/variant forms so the Stage 3 validator folds them
into the canonical tag instead of dumping them in `proposed_tags`. Target ~30–60
approved; it's fine to cut more. Anything you drop that turns out useful will
resurface as a `candidate` during migration.

Signals key: **3** = confirmed by 3 extractors (strong), **2** = two extractors.

## KEEP — strong (3-signal), grouped by domain

### Python / backend
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `python` | | 3 |
| `fastapi` | | 3 |
| `flask` | | 3 |
| `django` | | 3 |
| `streamlit` | | 3 |
| `celery` | | 3 |
| `postgresql` | `postgres` | 3 |
| `pytest` | | 3 |
| `sql` | | 2 |

### Web services / architecture
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `http` | | 3 |
| `soap` | | 3 |
| `rest` | | 3 |
| `api` | | 3 |
| `xml` | | 3 |
| `architecture` | `arquitectura`, `arq` | 3 |
| `message-broker` | `broker` | 3 |
| `worker` | | 3 |
| `web-service` | `servicio`, `service`, `serviz` | 2 |
| `ftp` | | 3 |

### DevOps / infra
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `devops` | `devop` | 3 |
| `docker` | | 3 |
| `github` | `git` | 3 |

### Graphics / VR
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `opengl` | | 3 |
| `rendering` | | 3 |
| `gpgpu` | | 3 |
| `gpu` | | 3 |
| `graphics` | `graphic`, `grafico` | 3 |

### Math
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `algebra` | | 3 |
| `math` | `matematica` | 3 |

### Programming (general)
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `programming` | `programacion` | 3 |

### Other
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `dss` | | 3 |
| `iiot` | | 3 |

## KEEP — consider (2-signal, LLM-backed → clean English)

### Web services / architecture
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `microservices` | `microserviz`, `microservicio` | 2 |
| `soa` | | 2 |
| `openapi` | `swagger`, `openapi` | 2 |
| `hexagonal-architecture` | | 2 |
| `integration` | | 2 |
| `task-queue` | `queue` | 2 |

### DevOps / infra
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `kubernetes` | | 2 |
| `container` | `contenedor`, `lxc` | 2 |
| `ci-cd` | `continuous-integration` | 2 |
| `devsecops` | `devsecop` | 2 |
| `cloud-computing` | `nube`, `cloud` | 2 |
| `sftp` | | 2 |

### Graphics / VR
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `shader` | `shading` | 2 |
| `cuda` | | 2 |
| `mesh` | `malla` | 2 |
| `texture` | `textura`, `texel` | 2 |
| `scene-graph` | `escena`, `scene` | 2 |
| `geometry` | `geometria` | 2 |
| `quaternion` | | 2 |
| `animation` | | 2 |
| `physics-simulation` | `simulation` | 2 |
| `aliasing` | | 2 |
| `glfw` | | 2 |
| `virtual-reality` | `virtual`, `realidad` | 2 |

### Agile / project management
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `agile` | | 2 |
| `scrum` | | 2 |
| `kanban` | | 2 |
| `sprint` | | 2 |

### Testing / security
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `testing` | | 2 |
| `security` | `seguridad` | 2 |
| `compliance` | | 2 |

### Data / IoT / tools
| canonical | aliases / variants | sig |
| --- | --- | --- |
| `iot` | | 2 |
| `statistics` | `estadistica` | 2 |
| `calculus` | `calculu`, `calculo` | 2 |
| `pydantic` | | 2 |
| `async` | `await` | 2 |
| `notion` | | 2 |
| `pkm` | | 2 |
| `vs-code` | | 2 |
| `pip` | `venv` | 2 |

## EXCLUDE — course/provenance admin (do NOT approve)

These describe *where a note came from*, not *what it's about*. Provenance already
lives in the `context` field and the folder path — tagging it here just pollutes
topic retrieval.

`bloque` · `bloque2` · `bloque3` · `examen` · `asignatura` · `semestre` ·
`master` · `uoc` · `ugr` · `upc` · `carrera` · `anual` · `horario` ·
`preinscripcion` · `apunte` · `nota` · `apartado` · `parte2` · `ej1` · `tarea` ·
`teoria` · `introduccion`

> Exception to decide: `grandvalira` is your work-project name — could be a real
> project tag rather than admin. Your call.

## EXCLUDE — too generic to retrieve on

Match almost everything → carry no signal. Drop unless you have a specific use.

`software` · `sistema` · `entorno` · `estructura` · `dato` · `dispositivo` ·
`funcion` · `codigo` · `objeto` · `work` · `nube` (kept as alias of cloud-computing) ·
`web` · `data` · `config` · `setup`
