# 03 — Module Production

**Public :** Responsables production, superviseurs d'équipe, directeur de production
**Durée :** 90 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Production :
1. Gestion des Recettes
2. Ouverture d'Ordre de Production
3. Démarrage et Suivi du Batch
4. Consommation de Matières (Dosage)
5. Enregistrement Produit Fini (IBC / Conteneur)
6. §22 Bilan Massique et COMPLÉMENT
7. Facteur d'Échelle
8. Campagne de Production
9. Traçabilité (Forward / Backward Trace)

---

## 1. Gestion des Recettes

### 1.1 Qu'est-ce qu'une Recette ?

Une recette définit les quantités de matières premières et les règles de mélange pour un produit fini (ex. `ADX-100` Superplasticizer). Chaque recette est **versionnée** — plusieurs versions peuvent exister pour le même produit, mais **une seule est active**.

### 1.2 Nouvelle Recette (Nouvelle Formulation)

**Chemin :** Menu gauche → **Production** → **Recettes** → **Nouvelle Formulation**

URL directe : `/portal/recete/yeni/`

1. **Produit fini :** Pour quel produit (liste déroulante)
2. **Référence parti (base) :** Ex. `1000` kg — quantité de base pour un batch
3. **Unité :** `kg` (défaut)
4. **Rendre cette recette active :** Si coché, l'ancienne recette active du même produit est automatiquement désactivée
5. Tableau **Composition — Matières Premières** :

| # | Matière Première | Qté / Lot | Tolérance % | Complément §22 |
|---|-----------------|-----------|-------------|----------------|
| 1 | W (Eau) | 600.0000 | 0.50 | ✅ |
| 2 | M1 (Monomère A) | 250.0000 | 0.50 | ⬜ |
| 3 | M2 (Monomère B) | 80.0000 | 0.50 | ⬜ |
| 4 | IN (Initiateur) | 15.0000 | 1.00 | ⬜ |
| 5 | NaOH | 47.0000 | 1.00 | ⬜ |

**Notes importantes :**
- La ligne **Complément §22** cochée effectue le remplissage automatique d'eau (bilan massique)
- Généralement, l'eau (W) est marquée comme complément
- Une seule ligne complément par recette
- Tolérances typiques : 0.5% (critique) ou 1.0% (souple)

6. **Notes :** Historique de développement, référence
7. Cliquez sur **Enregistrer la Recette**

### 1.3 Changer la Recette Active

Si plusieurs versions existent pour un produit :
- Aller à la liste des **Recettes**
- Ouvrir le détail de la recette souhaitée
- Cocher **« Rendre active »** + Enregistrer
- Le système désactive automatiquement l'autre

### 1.4 Consulter et Modifier une Recette

- Aller à la liste des recettes
- Cliquer sur la ligne
- Page de détail :
  - Produit + version
  - Base batch size + unité
  - État actif
  - Tableau des lignes
  - Notes

**Attention :** Modifier une recette active est **RISQUÉ** — elle est peut-être en cours d'utilisation. Créer une nouvelle version est plus sûr.

---

## 2. Ouverture d'Ordre de Production

Après la définition de la recette, un **ordre de production** est créé pour lancer la production réelle.

### 2.1 Nouvel Ordre de Production

**Chemin :** Interface admin → `/admin/production/productionorder/add/`

1. **N° Ordre :** Ex. `PORD-202608-005`
2. **Produit :** La recette active du produit est sélectionnée automatiquement
3. **Recette :** Recette active (modifiable)
4. **Quantité cible :** Ex. `2000` kg (2 batches × 1000 kg base)
5. **Unité :** `kg`
6. **Date planifiée :** Quand la production aura lieu
7. **Réacteur :** Dans quel réacteur (R-01, R-02, ...)
8. **Statut :** `PLANNED` (défaut)
9. **Notes :** Texte libre

### 2.2 Page Détail Ordre de Production

**Chemin :** Menu gauche → **Tableau de bord Production** → cliquer sur un ordre

Cette page est **très importante** — vous y :

- Saisissez le **Facteur d'échelle** avec aperçu
- Voyez le tableau **Besoins théoriques MP** (chaque matière première : besoin vs stock)
- Voyez le résumé **§22 Bilan massique**
- Le bouton **Démarrer Batch** s'active si le stock est suffisant

---

## 3. Facteur d'Échelle

Une recette est définie pour `1000 kg` par batch ; mais pour produire `2000 kg`, le facteur est `2.0`.

### 3.1 Changer l'Échelle

Dans le détail de l'ordre de production :
1. Saisissez `2.0` dans le champ **Facteur d'échelle**
2. Cliquez sur **Recalculer**
3. L'écran est mis à jour automatiquement :
   - Quantité cible : `2000 kg`
   - Eau (complément) : automatiquement `1200 kg`
   - Autres matières : `500 kg`, `160 kg` (2× recette)

### 3.2 §22 Bilan Massique — Comment ça marche ?

Recette : Eau (complément) = 600, Autres = 400 → Total 1000 kg
Échelle 2.0 → Cible 2000 kg
- Lignes fixes × 2 = 800 kg
- **Eau (complément) automatique = 2000 − 800 = 1200 kg**

C'est le standard de production algérien (§22 Bilan massique planifié) — critique en climat chaud.

### 3.3 Tableau Besoins Théoriques MP

Après saisie de l'échelle, le tableau ressemble à :

| Matière | Besoin | Stock (dispo) | Écart | Statut |
|---------|--------|---------------|-------|--------|
| W · Eau | 1.200,0000 | 7.919,3000 | +6.719 | ✓ |
| G · Gluconate de sodium | 30,0000 | 5.279,5000 | +5.249 | ✓ |
| SP · Superplastif. PCE | 700,0000 | 4.198,0000 | +3.498 | ✓ |
| HD · Composant | 70,0000 | 3.435,4000 | +3.365 | ✓ |

- **Toutes matières suffisantes** badge vert → bouton **Démarrer Batch** actif
- Si une matière manque → alerte rouge **Stock insuffisant**
- Le batch ne peut être lancé — reconstituez le stock ou réduisez le batch

---

## 4. Démarrer un Batch

### 4.1 Nouveau Batch

**Chemin :** Menu gauche → **Nouveau Batch**

Alternatif : depuis le détail de l'ordre → bouton **Démarrer Batch**

1. **Choisir l'ordre :** Sélectionner parmi les ordres actifs
2. **N° Batch :** Suggestion auto : `BATCH-20260915-042`
3. **Enregistrer**

En arrière-plan, le système :
- Crée l'enregistrement ProductionBatch
- Prépare un `MaterialConsumption` pour chaque matière première (poids réel encore vide)
- Le batch passe à l'état **PLANNED**

### 4.2 Cycle de Vie du Batch

```
PLANNED → IN_PROGRESS → COMPLETED → QC_HOLD → RELEASED
                                              ↘ REJECTED
```

- **PLANNED :** Batch préparé, production non commencée
- **IN_PROGRESS :** Dosage commencé (auto via SCADA)
- **COMPLETED :** Toutes matières dosées, mélange terminé
- **QC_HOLD :** En attente de contrôle qualité
- **RELEASED :** QA a approuvé, vendable
- **REJECTED :** QA a rejeté, destruction ou retraitement

---

## 5. Consommation de Matières (Dosage)

### 5.1 Enregistrement Manuel (sans SCADA)

**Chemin :** Admin → `/admin/production/materialconsumption/`

1. Sélectionner le batch
2. Pour chaque ligne matière :
   - Saisir le **poids réel**
   - Sélectionner le **lot** (FEFO suggéré automatiquement)
   - **Source :** `MANUAL`

Si l'écart dépasse la tolérance, le système passe automatiquement le batch en `QC_HOLD`.

### 5.2 Enregistrement Automatique via SCADA

Si le système SCADA est connecté :
- Node-RED envoie automatiquement un POST à la fin du batch
- `ProductionBatch` + `MaterialConsumption` + `QCTestResult` sont créés automatiquement dans ADMIX-ERP
- Le champ source devient `SCADA`

**Suivi portal :** Menu gauche → **SCADA** → flux des batches SCADA.

---

## 6. Enregistrement Produit Fini (Output Container / IBC)

Après la fin du batch, vous enregistrez dans quel IBC/citerne le produit a été rempli.

### 6.1 Nouveau Conteneur de Sortie

**Chemin :** Admin → `/admin/production/outputcontainer/add/`

1. **Batch :** Sélectionner le batch terminé
2. **Container (IBC) :** Quel conteneur rempli (ex. `IBC-OUT-01`)
3. **Quantité :** Ex. `500` kg
4. **Heure de remplissage**
5. **Référence expédition** (optionnel — ajouté lors de l'expédition)

Un batch peut remplir plusieurs IBC. Ex. 2000 kg batch → 4× IBC 500 kg.

---

## 7. Campagne de Production

Pour produire le même produit à la suite plusieurs fois, une campagne est utilisée (MES super batch).

### 7.1 Nouvelle Campagne

**Chemin :** Admin → `/admin/production/productioncampaign/add/`

1. **N° Campagne :** Ex. `CMP-2026-Q4-001`
2. **Produit + Recette + Réacteur**
3. **Nombre de batches planifiés :** Ex. `10`
4. **Cible totale :** Ex. `10.000` kg
5. **Dates début + fin**

Pendant la campagne, à chaque batch terminé, `completed_batch_count` s'incrémente automatiquement. Le pourcentage de progression est calculé (`progress_pct`).

---

## 8. Traçabilité (Forward / Backward Trace)

**Backward trace :** Voir de quels lots de matière un batch produit a été fait.
**Forward trace :** Un lot de matière première a affecté quels batches + est allé chez quels clients ?

### 8.1 Backward Trace

**Chemin :** Admin → détail ProductionBatch → **Actions** → **Backward Trace**

Résultat JSON :
```json
{
  "batch_number": "BATCH-20260915-042",
  "consumptions": [
    {"raw_material": "W", "lot_number": "LOT-W-202606-014", "supplier": "MC-Bauchemie"},
    {"raw_material": "M1", "lot_number": "LOT-M1-202607-023", "supplier": "BASF"}
  ]
}
```

### 8.2 Forward Trace

**Chemin :** Admin → détail RawMaterialLot → **Actions** → **Forward Trace**

Résultat JSON :
```json
{
  "lot_number": "LOT-W-202606-014",
  "batches": ["BATCH-2026-041", "BATCH-2026-042"],
  "shipments": ["BL-2026-100", "BL-2026-102"],
  "customers": ["C-2026-001 SARL Cimenterie Blida"]
}
```

**Utilisation :** Lors d'une réclamation client, retrouvez le batch problématique — puis les lots utilisés — puis les autres batches touchés — puis les autres clients concernés.

---

## 9. Suivi Portal

### 9.1 Tableau de Bord Production

**Chemin :** Menu gauche → **Tableau de bord Production**

Cette page affiche :
- Batches actifs (20 derniers)
- Ordres de production planifiés (~10)
- État d'occupation des réacteurs
- Nombre de productions 30 jours + taux de release
- Nombre de recettes actives

### 9.2 Rapport Rendements Production

**Chemin :** Menu gauche → **Rapports** → **Rendements Production**

- 90 derniers jours + 100 derniers batches
- Rendement moyen
- Pour chaque batch : cible vs réel, delta, rendement %
- Code couleur : ≥98% vert, 95-98% jaune, <95% rouge

---

## 10. Tableau de Bord SCADA

Si le SCADA est utilisé :

**Chemin :** Menu gauche → **SCADA**

- État du pont (en ligne / hors ligne)
- Batches aujourd'hui + semaine
- Graphique d'activité 24h
- 20 derniers batches SCADA (n° batch, recette, rendement %)
- État de l'utilisateur pont + token

Cet écran montre si Node-RED de l'intégrateur fonctionne correctement.

---

## 11. FAQ

**Q : J'ai changé le facteur d'échelle mais les besoins théoriques ne se mettent pas à jour ?**
R : Cliquez sur **Recalculer**. Le changement ne s'applique qu'au clic.

**Q : Ligne complément cochée mais quantité affiche 0 ?**
R : Le champ `quantity` de la ligne recette doit aussi être rempli (petite valeur initiale, ex. `600`). Le drapeau complément écrase le calcul mais la ligne doit être définie.

**Q : Impossible de démarrer un batch, bouton grisé ?**
R : Une matière première apparaît en **rouge** dans le tableau des besoins — stock insuffisant. Vérifiez le magasin ou réduisez le batch.

**Q : J'ai créé deux recettes actives pour le même produit, que se passe-t-il ?**
R : Le système l'empêche — `Recipe.save()` désactive automatiquement l'ancienne. Seule la dernière modifiée reste active.

**Q : Un batch SCADA est arrivé mais je ne le vois pas dans le portal ?**
R : Consultez le **tableau SCADA**. S'il n'y est pas non plus, le POST de Node-RED a échoué. Contactez l'intégrateur.

**Q : La tolérance a été dépassée, batch en QC_HOLD. Que faire ?**
R : Informez QA. Ils décident `RELEASED` ou `REJECTED`. Un retraitement est possible.

**Q : Si un batch d'une campagne est annulé, le total diminue-t-il ?**
R : Non, `planned_batch_count` est fixe. `completed_batch_count` n'augmente qu'avec les batches terminés. Les annulés ne sont pas comptés.

---

## 12. Exercices Pratiques

1. **Nouvelle recette :** 5 lignes, une en complément (eau), tolérance 0.5%
2. **Ordre de production :** cible 3000 kg, date planifiée dans 3 jours
3. **Test échelle :** Appliquer facteurs 1.5 et 2.0 sur le même ordre, comparer besoins
4. **Batch manuel :** Doser manuellement chaque matière + remplir un IBC
5. **Backward trace :** Lister les lots utilisés pour un batch terminé

Une fois chaque exercice terminé, montrez au directeur de production.
