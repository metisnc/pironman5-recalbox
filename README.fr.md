# Pironman 5 pour Recalbox

[English](README.md) | **Français**

Fait fonctionner les équipements du boîtier
[SunFounder Pironman 5](https://www.sunfounder.com/) sous
[Recalbox](https://www.recalbox.com/) : écran OLED d'état, ventilateurs du
boîtier et LEDs RGB, sur Raspberry Pi 5. Pironman 5 et Pironman 5 Max sont
pris en charge.

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
- [Menu Recalbox](#menu-recalbox)
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
| En jeu | Pendant une partie, l'OLED affiche le système, le titre, la durée de jeu, le CPU, la RAM et la température |
| Menu Recalbox | LEDs, ventilateurs et écran se règlent depuis *Menu > Scripts utilisateur*, appliqués aussitôt et confirmés sur l'OLED |
| Couleur par système | Pendant une partie, les LEDs prennent la couleur du constructeur de la console (Nintendo rouge, Sega bleu…) |
| Ventilateurs du boîtier | Suivent le ventilateur du Raspberry Pi 5 : allumés à partir d'environ 50 °C par défaut, cinq modes disponibles |
| LEDs des ventilateurs (Max) | Suivent les ventilateurs, comme les LEDs RGB, toujours allumées ou toujours éteintes |
| Veille synchronisée | L'OLED et les LEDs RGB s'éteignent pendant l'écran de veille d'EmulationStation |
| LEDs RGB | 4 LEDs WS2812 : fixe, respiration, défilement, arc-en-ciel, cycle de teinte ; couleur, luminosité et vitesse réglables |
| Ventilateur du Raspberry Pi 5 | Laissé au pilote du noyau Recalbox, comme sur un système d'origine |
| Empreinte | Environ 2 % d'un cœur CPU et 30 Mo de RAM, en priorité basse pour laisser la main aux jeux |

## Compatibilité

| Élément | Pris en charge |
|---|---|
| Recalbox | 11.0 (testé sur `11.0-patron-1.1`) |
| Carte | Raspberry Pi 5 |
| Boîtier | Pironman 5, Pironman 5 Max |

Non pris en charge : Pironman 5 Mini, Pro Max et NAS, autres modèles de
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
wget -qO- https://raw.githubusercontent.com/metisnc/pironman5-recalbox/main-pr5-rc/recalbox/install.sh | bash
```

L'installateur demande le modèle de boîtier (les deux se présentent comme
« Pironman 5 » dans leur EEPROM) : tapez `1` pour le Pironman 5 ou `2` pour
le Pironman 5 Max, puis confirmez. Pour ne pas avoir la question, ajoutez
`-s -- --variant base` ou `-s -- --variant max` après `bash`. Lors d'une mise
à jour, le modèle déjà installé est proposé par défaut.

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
git clone -b main-pr5-rc https://github.com/metisnc/pironman5-recalbox.git
bash pironman5-recalbox/recalbox/build-offline-bundle.sh pironman5-offline
scp -r pironman5-recalbox pironman5-offline root@recalbox.local:/recalbox/share/
ssh root@recalbox.local \
  'bash /recalbox/share/pironman5-recalbox/recalbox/install.sh --offline /recalbox/share/pironman5-offline'
```

Remplacez `recalbox.local` par l'adresse de votre Recalbox si nécessaire.

## Menu Recalbox

L'installateur ajoute des entrées dans **Menu > Scripts utilisateur**
d'EmulationStation, nommées dans la langue de Recalbox. Chaque entrée indique
la valeur actuelle entre parenthèses et le résultat qu'elle produit :

| Entrée | Effet |
|---|---|
| `Pironman · LEDs · allumage → éteindre` | allume ou éteint les LEDs |
| `Pironman · LEDs · couleur (cyan) → bleu` | couleur suivante : blanc, rouge, orange, jaune, vert, cyan, bleu, violet, rose |
| `Pironman · LEDs · luminosité (25 %) → 50 %` | 25, 50, 75 ou 100 % |
| `Pironman · LEDs · selon le système → activer` | couleur des LEDs selon le constructeur pendant les parties |
| `Pironman · LEDs · style (défilement) → arc-en-ciel` | fixe, respiration, défilement, arc-en-ciel, cycle de couleurs |
| `Pironman · Ventilateurs · LEDs (suivre) → comme les RGB` | LEDs des ventilateurs : suivre les ventilateurs, comme les LEDs RGB, allumées, éteintes (Max uniquement) |
| `Pironman · Ventilateurs · mode (performance) → frais` | toujours, performance, frais, équilibré, silencieux |
| `Pironman · Veille · synchronisation → désactiver` | OLED et LEDs éteints pendant l'écran de veille d'EmulationStation |
| `Pironman · Écran · allumage → éteindre` | allume ou éteint l'écran OLED |

Les changements s'appliquent immédiatement et sont enregistrés. L'OLED
confirme chacun pendant 3 secondes, et le message de Recalbox reprend le nom
de l'entrée. Les entrées sont renommées après chaque changement et gardent
leur place dans le menu : ressortez de *Scripts utilisateur* puis revenez-y
pour voir les nouveaux noms (EmulationStation lit les noms à l'ouverture du
menu).

Pendant une partie, l'OLED affiche uniquement la page **En jeu** ; les pages
habituelles reviennent en quittant le jeu. Avec *selon le système* activé,
les LEDs prennent la couleur du constructeur (Nintendo rouge, Sega bleu, Sony
violet, SNK cyan, NEC orange, Atari jaune, Bandai rose, Microsoft vert,
arcade magenta) puis reviennent à votre couleur.

Les mêmes réglages sont accessibles en SSH :

```bash
python3 /recalbox/share/pironman5/app/recalbox/pironman5ctl.py --help
python3 /recalbox/share/pironman5/app/recalbox/pironman5ctl.py set rgb_brightness 50
```

## Configuration

Les réglages sont dans `/recalbox/share/pironman5/config.json`, accessible
aussi via le partage réseau de Recalbox. Modifiez les valeurs de la section
`system` : les changements sont appliqués en moins d'une seconde, sans
redémarrer le service.

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
| `oled_game_page` | `true`, `false` : page En jeu pendant les parties | `true` |
| `rgb_system_colors` | `true`, `false` : couleur des LEDs selon le constructeur pendant les parties | `true` |
| `sleep_sync` | `true`, `false` : OLED et LEDs RGB éteints pendant l'écran de veille | `true` |
| `gpio_fan_led` | `follow`, `rgb` (comme les LEDs RGB), `on`, `off` : LEDs des ventilateurs (Max) | `follow` |
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
éteints), retire les entrées du menu et l'entrée de démarrage de
`custom.sh`, et déplace
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
| Les réglages sont ignorés | `config.json` est un JSON valide (voir `logs/pironman5.log`) |
| Entrées du menu absentes | lancez `pironman5ctl.py install-scripts`, puis rouvrez *Scripts utilisateur* |

## Limites

- Le tableau de bord web et l'historique (InfluxDB) du logiciel officiel ne
  sont pas inclus, pour limiter l'empreinte.
- Le bouton d'alimentation du Raspberry Pi 5 reste géré par Recalbox : les
  pages de l'OLED défilent automatiquement au lieu de changer avec le bouton.
- Les températures des disques ne sont pas affichées.
- EmulationStation ne sait pas afficher de notification personnalisée : les
  noms des entrées du menu portent l'information, et se mettent à jour à la
  réouverture de *Scripts utilisateur*.
- Activer la prise en charge `hat.wpaf` (ventilateur/OLED) de Recalbox ou les
  manettes GPIO (`controllers.gpio`) entre en conflit avec ce service (bus
  I2C et broches GPIO partagés).

## Fonctionnement

Le service exécute le logiciel officiel SunFounder `pironman5`, sans
modification, via un lanceur qui l'adapte à Recalbox : réglages et journaux
sur la partition share, pas de systemd, pas de `lsblk`, système de fichiers
exFAT, ainsi que l'intégration à Recalbox (entrées du menu, événements de
jeu d'EmulationStation). Détails techniques (en anglais) :
[recalbox/README.md](recalbox/README.md).

| Chemin | Contenu |
|---|---|
| `pironman5/` | paquet SunFounder `pironman5` (upstream) |
| `recalbox/` | installateur, désinstallateur, script de service et lanceur Recalbox |

## Crédits et licence

Portage Recalbox © 2026 metisnc. Basé sur [sunfounder/pironman5](https://github.com/sunfounder/pironman5),
[pm_auto](https://github.com/sunfounder/pm_auto) et
[sf_rpi_status](https://github.com/sunfounder/sf_rpi_status) de SunFounder.

Sous licence GNU General Public License v2.0, voir [LICENSE](LICENSE) et
[NOTICE](NOTICE).
