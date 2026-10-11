# Pironman 5 pour Recalbox

[English](README.md) | **Français**

Fait fonctionner les équipements du boîtier
[SunFounder Pironman 5](https://www.sunfounder.com/) sous
[Recalbox](https://www.recalbox.com/) : écran OLED d'état, ventilateurs du
boîtier et LEDs RGB, sur Raspberry Pi 5.

L'installateur officiel du Pironman 5 vise Raspberry Pi OS (apt, systemd,
environnement virtuel dans `/opt`, InfluxDB) et ne peut pas fonctionner sous
Recalbox. Ce projet fournit un installateur dédié qui place tout dans la
partition persistante `/recalbox/share`, ne modifie jamais `/boot` ni l'image
système, et résiste aux redémarrages comme aux mises à jour de Recalbox.

> Projet communautaire, sans lien avec SunFounder ni Recalbox.

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Compatibilité](#compatibilité)
- [Installation](#installation)
- [Configuration](#configuration)
- [Gestion du service](#gestion-du-service)
- [Désinstallation](#désinstallation)
- [Mises à jour de Recalbox](#mises-à-jour-de-recalbox)
- [Dépannage](#dépannage)
- [Limites](#limites)
- [Fonctionnement](#fonctionnement)
- [Crédits et licence](#crédits-et-licence)

## Fonctionnalités

| Fonction | Détails |
|---|---|
| Écran OLED | Adresses IP (Ethernet et Wi-Fi), charge et température du CPU, RAM, occupation des disques ; les pages défilent automatiquement |
| Ventilateurs du boîtier | Suivent le ventilateur du Raspberry Pi 5 : allumés à partir d'environ 50 °C par défaut, cinq modes disponibles |
| LEDs RGB | 4 LEDs WS2812 : fixe, respiration, défilement, arc-en-ciel, cycle de teinte ; couleur, luminosité et vitesse réglables |
| Ventilateur du Raspberry Pi 5 | Laissé au pilote du noyau Recalbox, comme sur un système d'origine |
| Empreinte | Environ 2 % d'un cœur CPU et 30 Mo de RAM, en priorité basse pour laisser la main aux jeux |

## Compatibilité

| Élément | Pris en charge |
|---|---|
| Recalbox | 11.0 (testé sur `11.0-patron-1.1`) |
| Carte | Raspberry Pi 5 |
| Boîtier | Pironman 5 |

Non pris en charge : Pironman 5 Mini, Max, Pro Max et NAS, autres modèles de
Raspberry Pi.

## Installation

Prérequis :

- le Pironman 5 monté sur un Raspberry Pi 5 sous Recalbox 11 ;
- un accès SSH à la Recalbox en `root` (identifiants : voir la
  [documentation Recalbox](https://wiki.recalbox.com/)) ;
- une connexion Internet sur la Recalbox, ou
  l'[installation hors ligne](#installation-hors-ligne).

Rien à activer dans `/boot` : le firmware du Raspberry Pi détecte le
Pironman 5 et charge automatiquement son overlay device tree (I2C et SPI).

### Installation en ligne

Connectez-vous à la Recalbox en SSH et lancez :

```bash
wget -qO- https://raw.githubusercontent.com/metisnc/pironman5-recalbox/v1/recalbox/install.sh | bash
```

Le service démarre aussitôt : l'écran OLED, les LEDs RGB et les ventilateurs
du boîtier s'allument en quelques secondes.

L'installateur :

1. vérifie le système (Recalbox, Raspberry Pi 5, Python 3.11, Pironman 5) ;
2. sauvegarde les fichiers qu'il peut affecter dans
   `/recalbox/share/pironman5-backups/<date>/` ;
3. télécharge les dépendances, figées sur des versions testées et vérifiées
   par somme de contrôle (paquets précompilés uniquement, aucun compilateur
   requis) ;
4. installe le tout dans `/recalbox/share/pironman5/` ;
5. déclare le service dans `/recalbox/share/system/custom.sh`, que Recalbox
   exécute au démarrage et à l'arrêt ;
6. démarre le service.

Relancer l'installateur met l'installation à jour en conservant vos
réglages.

### Installation hors ligne

Sur un ordinateur disposant d'Internet, de Python 3 et de Git :

```bash
git clone -b v1 https://github.com/metisnc/pironman5-recalbox.git
bash pironman5-recalbox/recalbox/build-offline-bundle.sh pironman5-offline
scp -r pironman5-recalbox pironman5-offline root@recalbox.local:/recalbox/share/
ssh root@recalbox.local \
  'bash /recalbox/share/pironman5-recalbox/recalbox/install.sh --offline /recalbox/share/pironman5-offline'
```

Remplacez `recalbox.local` par l'adresse de votre Recalbox si nécessaire.

## Configuration

Les réglages sont dans `/recalbox/share/pironman5/config.json`, accessible
aussi via le partage réseau de Recalbox. Modifiez les valeurs de la section
`system`, puis [redémarrez le service](#gestion-du-service).

| Clé | Valeurs | Défaut |
|---|---|---|
| `rgb_enable` | `true`, `false` | `true` |
| `rgb_style` | `solid`, `breathing`, `flow`, `flow_reverse`, `rainbow`, `rainbow_reverse`, `hue_cycle` | `breathing` |
| `rgb_color` | couleur hexadécimale, ex. `"#0a1aff"` | `"#0a1aff"` |
| `rgb_brightness` | `0` à `100` | `100` |
| `rgb_speed` | `0` à `100` | `50` |
| `oled_enable` | `true`, `false` | `true` |
| `oled_pages` | liste parmi `mix`, `performance`, `ips`, `disk` | les quatre |
| `oled_page_interval` | secondes entre deux pages, `0` pour rester sur la première | `10` |
| `oled_rotation` | `0`, `180` | `0` |
| `oled_sleep_timeout` | secondes avant extinction de l'écran, `0` = jamais | `0` |
| `temperature_unit` | `C`, `F` | `C` |
| `gpio_fan_mode` | ventilateurs du boîtier : `0` toujours allumés, `1` performance, `2` frais, `3` équilibré, `4` silencieux | `1` |
| `debug_level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

`gpio_fan_mode` fixe le niveau du ventilateur du Raspberry Pi 5 à partir
duquel les ventilateurs du boîtier s'allument : `1` vers 50 °C, `2` vers
60 °C, `3` vers 67 °C, `4` vers 75 °C.

Laissez `oled_sleep_timeout` à `0` : Recalbox garde la main sur le bouton
d'alimentation, donc rien ne rallume l'écran une fois éteint.

## Gestion du service

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh restart
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh stop
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh start
```

Les journaux sont dans `/recalbox/share/pironman5/logs/` : `pironman5.log`
(limité à 3 Mo au total) et `console.log` (sortie du dernier démarrage).

## Désinstallation

```bash
bash /recalbox/share/pironman5/app/recalbox/uninstall.sh
```

La désinstallation arrête le service (écran, LEDs et ventilateurs du boîtier
éteints), retire l'entrée de démarrage de `custom.sh` et déplace
l'installation dans `/recalbox/share/pironman5-backups/uninstall-<date>/`.
Rien n'est supprimé : effacez vous-même `/recalbox/share/pironman5-backups`
quand vous n'en avez plus besoin.

Pour retrouver vos réglages après une réinstallation, copiez `config.json`
depuis le dossier de sauvegarde vers `/recalbox/share/pironman5/` puis
redémarrez le service.

## Mises à jour de Recalbox

Les mises à jour de Recalbox remplacent l'image système mais conservent
`/recalbox/share`, où se trouvent l'installation et son entrée de démarrage :
le service continue de fonctionner après une mise à jour. Pour le vérifier :

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
```

La commande signale un avertissement si le point de démarrage ou les
périphériques I2C/SPI sont absents. Si une future version de Recalbox
embarque une autre version de Python que la 3.11, le service ne démarrera
plus tant qu'une version adaptée de ce projet n'aura pas été installée.

## Dépannage

| Symptôme | Vérification |
|---|---|
| Rien ne fonctionne | `status` ci-dessus, puis `logs/console.log` et `logs/pironman5.log` |
| L'écran OLED reste noir | `cat /proc/device-tree/hat/product` affiche `Pironman 5` ; `i2cdetect -y 1` affiche `3c` |
| Les LEDs RGB restent éteintes | `ls /dev/spidev0.0` ; `rgb_enable` et `rgb_brightness` dans `config.json` |
| Les ventilateurs du boîtier ne s'arrêtent jamais | `gpio_fan_mode` vaut `0` (toujours allumés) |
| Les réglages sont ignorés | `config.json` est un JSON valide ; redémarrez le service après modification |

## Limites

- Le tableau de bord web et l'historique (InfluxDB) du logiciel officiel ne
  sont pas inclus, pour limiter l'empreinte.
- Le bouton d'alimentation du Raspberry Pi 5 reste géré par Recalbox : les
  pages de l'OLED défilent automatiquement au lieu de changer avec le bouton.
- Les températures des disques ne sont pas affichées.
- Activer la prise en charge `hat.wpaf` (ventilateur/OLED) de Recalbox ou les
  manettes GPIO (`controllers.gpio`) entre en conflit avec ce service (bus
  I2C et broches GPIO partagés).

## Fonctionnement

Le service exécute le logiciel officiel SunFounder `pironman5`, sans
modification, via un lanceur qui l'adapte à Recalbox : réglages et journaux
sur la partition share, pas de systemd, pas de `lsblk`, système de fichiers
exFAT. Détails techniques (en anglais) :
[recalbox/README.md](recalbox/README.md).

| Chemin | Contenu |
|---|---|
| `pironman5/` | paquet SunFounder `pironman5` (upstream) |
| `recalbox/` | installateur, désinstallateur, script de service et lanceur Recalbox |

## Crédits et licence

Basé sur [sunfounder/pironman5](https://github.com/sunfounder/pironman5),
[pm_auto](https://github.com/sunfounder/pm_auto) et
[sf_rpi_status](https://github.com/sunfounder/sf_rpi_status) de SunFounder.

Sous licence GNU General Public License v2.0, voir [LICENSE](LICENSE).
