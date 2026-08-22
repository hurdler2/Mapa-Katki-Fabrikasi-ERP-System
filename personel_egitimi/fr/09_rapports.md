# 09 — Rapports Direction

**Public :** Directeur général, direction, directeur financier, directeur production, directeur qualité
**Durée :** 60 minutes
**Prérequis :** `01_introduction.md` lu + documents module concernés

Ce document couvre l'ensemble des rapports :
1. Centre de Rapports (Hub)
2. Tableau de Bord Comptabilité
3. Échéancier Clients
4. Échéancier Fournisseurs
5. Valorisation Stocks
6. Rendements Production
7. BL-Facture Matching
8. Relevé de Compte Client
9. Tableau SCADA
10. Quel Rapport à Quel Moment ?

---

## 1. Centre de Rapports (Hub)

### 1.1 Accès Central

**Chemin :** Menu gauche → **Rapports Direction** → **Centre de Rapports**

URL directe : `/portal/rapor/`

Vue d'ensemble financière de l'entreprise.

### 1.2 Cartes KPI (4 en Haut)

| KPI | Description |
|-----|-------------|
| **Revenus facturés (mois)** | Total factures émises ce mois (TTC) |
| **Charges totales (mois)** | Dépenses + factures d'achat |
| **Résultat net** | Revenus − Charges (Bénéfice/Perte) |
| **Ce mois revenus** | Résumé revenus facturés |

### 1.3 Cartes Rapport (6 Cliquables)

1. **Résultat financier** — P&L théorique + trésorerie
2. **Échéancier clients** — Aging créances
3. **Échéancier fournisseurs** — Aging dettes
4. **Rendements production** — Analyse rendements
5. **Répartition dépenses** — Par catégorie
6. **Valorisation stocks** — Valeur inventaire
7. **BL-Facture matching**

### 1.4 Fréquence d'Utilisation

- **DG :** hebdomadaire — KPI haut niveau
- **DAF :** quotidien — Échéancier clients + BL-Facture
- **Directeur Prod :** hebdomadaire — Rendements
- **Directeur Magasin :** mensuel — Valorisation

---

## 2. Tableau de Bord Comptabilité

### 2.1 Accès

**Chemin :** Menu gauche → **Tableau de bord Comptabilité**

URL directe : `/portal/muhasebe/`

### 2.2 Contenu

**8 Cartes KPI :**
- Encaissements du jour
- Encaissements du mois
- Créances ouvertes
- Échéances de la semaine
- BL non facturés
- Chèques en attente
- Alertes chèques sans provision
- Avances actives

**6 Graphiques Chart.js :**
- Tendance revenus/charges mensuelle
- Répartition méthodes paiement
- Aging bar
- TVA mensuelle
- Top clients
- Statut factures pie

**2 Tableaux :** Chèques post-datés, factures en retard

### 2.3 Utilisation

Chaque matin **5 minutes** :
- Chèques échus ? → encaisser
- Chèque sans provision ? → contacter client
- Client en zone rouge aging → lancer recouvrement

---

## 3. Échéancier Clients

### 3.1 Accès

**Chemin :** Menu gauche → **Rapports** → **Échéancier Clients**

URL directe : `/portal/rapor/echeancier-clients/`

### 3.2 Tranches (5 Groupes d'Âge)

| Tranche | Signification | Couleur |
|---------|--------------|---------|
| **Non échu** | Échéance future | Vert |
| **0-30 j** | Récent en retard | Bleu |
| **31-60 j** | Retard moyen | Jaune |
| **61-90 j** | Retard sérieux | Jaune-Rouge |
| **90+ j** | Risque critique | Rouge |

### 3.3 Répartition par Client

Tableau par client :
- Montant non échu
- 0-30, 31-60, 61-90, 90+
- **TOTAL**
- Bouton **Détail** → compte client

### 3.4 Scénarios

**Scénario 1 — Réunion recouvrement hebdo :**
- Focus 90+ → actions par client (appel, courrier, visite, juridique)

**Scénario 2 — Réunion direction mensuelle :**
- Tendance créances ouvertes
- DSO moyen
- Liste clients critiques

**Scénario 3 — Provision annuelle :**
- Créances 180+ jours → provision doutes
- Info comptabilité

---

## 4. Échéancier Fournisseurs

### 4.1 Accès

**Chemin :** Menu gauche → **Rapports** → **Échéancier Fournisseurs**

*(Actuellement admin — portal à venir)*

### 4.2 Structure

Identique à l'aging clients, côté **dettes**.

### 4.3 Utilisation

- Priorité paiements
- Planification cash
- Opportunités escompte early payment
- Suivi échéances

---

## 5. Valorisation Stocks

### 5.1 Accès

**Chemin :** Menu gauche → **Rapports** → **Valorisation Stocks**

URL directe : `/portal/rapor/valorisation-stocks/`

### 5.2 Contenu

**Cartes KPI :**
- Valeur totale MP (DZD)
- Nombre de MP

**Tableau :**
| Code | Nom | Quantité | Coût moyen | Valeur | Niveau |
|------|-----|----------|------------|--------|--------|
| G | Gluconate sodium | 5.279,50 kg | 265,80 | 1.403.299,00 | ✓ |
| HD | Composant | 3.435,40 kg | 332,48 | 1.142.203,70 | ⚠ Alerte |

**TOTAL** en bas.

### 5.3 Scénarios

**Scénario 1 — Inventaire fin mois :**
- Valeur stock comptable
- Reporting déclaration fiscale

**Scénario 2 — Optimisation cash :**
- Stocks lents/chers → réduire commandes
- Stocks bas (rupture) → achat urgent

**Scénario 3 — Alerte rupture :**
- MP en rupture → production risquée
- Bon de commande urgent

---

## 6. Rendements Production

### 6.1 Accès

**Chemin :** Menu gauche → **Rapports** → **Rendements Production**

URL directe : `/portal/rapor/rendements-production/`

### 6.2 Contenu

**3 Cartes KPI :**
- Total Cible (kg — 90 jours)
- Total Réel
- **Rendement Moyen** (%)

**Code couleur :**
- 🟢 ≥98% — Excellent
- 🟠 95-98% — Acceptable
- 🔴 <95% — Problème

**Tableau (100 derniers batches) :**
| Batch | Produit | Cible | Réel | Delta | Rendement |
|-------|---------|-------|------|-------|-----------|
| BATCH-202509-024 | ADX-100 | 1.404,00 | 1.432,08 | +28,08 | 102% |

### 6.3 Scénarios

**Scénario 1 — Révision recette :**
- Produit < 95% constant → recette à revoir
- Ex. bilan massique complément excédentaire

**Scénario 2 — Analyse réacteur :**
- Même recette, rendements différents par réacteur
- Étalonnage réacteur (CMMS)

**Scénario 3 — Performance opérateur :**
- Rendement bas même équipe → besoin formation
- Delta systématiquement négatif → étalonnage capteur dosage

---

## 7. BL-Facture Matching

Détail dans `06_ventes.md` § 10.

**Chemin :** Menu gauche → **Rapports** → **BL-Facture Matching**

URL directe : `/portal/rapor/bl-fatura/`

**KPI :** Matchés, En attente, **Montant en attente** (critique cash), Annulés

**Utilisation :** BL en attente → facturation rapide → amélioration cash.

---

## 8. Relevé de Compte Client

### 8.1 Accès

Depuis l'aging → cliquer sur un client → bouton **Détail**

URL directe : `/portal/muhasebe/cari/<customer_pk>/`

### 8.2 Contenu

**4 Cartes KPI :**
- Total Factures (TTC)
- Total Paiements
- Avance Ouverte
- **Solde** — créancier / soldé

**Tableau 1 — Factures**
**Tableau 2 — Avances (§23)**

### 8.3 Scénarios

**Scénario 1 — Entretien client :**
- Client demande solde → afficher relevé
- Capture écran + envoyer

**Scénario 2 — Rapprochement fin année :**
- Comptabilité vs. registres client
- Écart → détailler (facture ou paiement manquant ?)

**Scénario 3 — Analyse doutes :**
- Factures 90+ jours
- Client en retard chronique → score risque

---

## 9. Tableau SCADA

### 9.1 Accès

**Chemin :** Menu gauche → **SCADA**

URL directe : `/portal/scada/`

### 9.2 Contenu

**4 Cartes KPI :**
- **État du pont** — EN LIGNE / En attente
- Batches SCADA du jour
- Batches SCADA de la semaine
- Total batches SCADA

**Panneau Identité & API :**
- Utilisateur pont statut
- Date création token
- 8 derniers caractères token
- Liste endpoints API

**Graphique Activité 24h :** Bar chart horaire

**Tableau 20 derniers batches SCADA**

### 9.3 Diagnostic

- **Pont HORS LIGNE** → Pas de communication SCADA. Alerter IT/intégrateur.
- **Rendement <95%** → problème dosage SCADA. Alerter directeur production.
- **Tableau vide** → Système récemment installé ou batches n'arrivent pas. Vérifier configuration intégrateur.

---

## 10. Quel Rapport à Quel Moment ?

### 10.1 Quotidien (5 min)

- **Tableau comptabilité :** chèques échus + sans provision
- **Tableau SCADA :** batches aujourd'hui + état pont

### 10.2 Hebdomadaire (30 min)

- **KPI Centre de Rapports :** revenus vs charges
- **Aging clients :** 90+ → actions recouvrement
- **BL-Facture :** priorité facturation

### 10.3 Mensuel (2 h)

- **Tableau comptabilité détaillé** — tendances
- **Valorisation stocks** — inventaire, ruptures
- **Rendements production** — analyse
- **Compte client (top 10)** — croissance annuelle

### 10.4 Trimestriel (Conseil)

- P&L Centre de Rapports
- Portefeuille clients
- Performance fournisseurs
- Métriques qualité (taux FAIL, NCR, CAPA)

### 10.5 Annuel (Audit + Fiscal)

- P&L annuel (SCF PCN 2010)
- Balance complète
- Valeur inventaire (31 déc)
- Déclaration TVA annuelle (12 G50)
- Préparation audit FPC + ISO 9001

---

## 11. FAQ

**Q : Quelle devise dans les rapports ?**
R : Tout en **DZD** (Dinar Algérien). Format algérien : `1.234.567,89 DZD`.

**Q : Comment sont calculées les tranches aging ?**
R : Écart entre échéance facture et aujourd'hui. Si `due_date` vide → `date` (date facture) utilisée.

**Q : Pourquoi valeur stock ≠ balance ?**
R : Comptabilité stock périodique (fin mois). Portal rapport **live**. Se réconcilie à la clôture.

**Q : Rendement SCADA différent des batches manuels ?**
R : SCADA plus précis. Manuel → erreur opérateur possible.

**Q : Relevé client téléchargeable en PDF ?**
R : Actuellement non — capture écran + export Excel à venir.

**Q : Snapshot mensuel possible ?**
R : Ctrl+P navigateur → PDF. Snapshot auto à venir.

**Q : Batch pas visible dans SCADA ?**
R : Batch non préfixé `SCADA-` (créé manuel). Batches SCADA : `production_order.order_number` commence par `SCADA-`.

---

## 12. Exercices Pratiques

1. **Centre rapports :** 5 minutes tous KPI, prendre notes
2. **Aging :** Top 3 clients risque, recommandations d'action
3. **Rendements :** Batches <95% d'un produit, causes possibles
4. **Compte client :** Capture écran relevé
5. **SCADA :** Heure la plus active des 24 dernières heures

Montrer au directeur concerné.
