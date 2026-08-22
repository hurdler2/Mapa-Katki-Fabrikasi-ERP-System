# 08 — Module Conformité Légale

**Public :** Responsable conformité, directeur qualité, responsable export
**Durée :** 90 minutes
**Prérequis :** `01_introduction.md` et `04_qualite.md` lus

Ce document couvre l'ensemble du module Conformité :
1. SDS (Safety Data Sheet)
2. DoP (Declaration of Performance) + Marquage CE
3. Notified Body et Audit FPC
4. CoC (Certificate of Conformity)
5. Suivi REACH SVHC
6. Méthodes Test EN 480
7. Échantillon de Rétention
8. Compatibilité Stockage
9. Conformité Algérie (SCF, TVA G50, DGI)

---

## 1. SDS (Safety Data Sheet)

### 1.1 Qu'est-ce que la SDS ?

Document légal 16 sections pour usage sûr d'un produit chimique :
- **EU Reg 2020/878** (nouveau format SDS)
- **REACH Reg 1907/2006**
- Étiquetage **GHS/CLP**

En Algérie : SDS conforme au CLP français obligatoire.

### 1.2 Liste SDS

**Chemin :** Menu gauche → **Conformité** → **SDS (16 Sections)**

URL directe : `/portal/uyum/sds/`

**Cartes KPI :** Total, Brouillons, Approuvées

**Tableau :**
- N° SDS
- Profil (chimique)
- v (version)
- Langue (`fr`, `en`, `ar`, `tr`)
- Date révision
- **Badge statut :**
  - 🟢 Approuvée
  - 🟠 Brouillon
  - ⚫ Superseded / Withdrawn
- **Bouton 📄 PDF**

### 1.3 Nouvelle SDS

**Chemin :** Admin → `/admin/chemicals/safetydatasheet/add/`

1. **N° SDS :** Ex. `SDS-ADX-100-v3-fr`
2. **Profil chimique**
3. **Version :** `1.0`, `2.0`
4. **Langue :** `fr` (défaut Algérie)
5. **Dates :** émission, révision, prochaine revue
6. **16 sections** (chacune TextField) :
   1. Identification
   2. Identification des dangers
   3. Composition / ingrédients
   4. Premiers secours
   5. Mesures anti-incendie
   6. Rejet accidentel
   7. Manipulation et stockage
   8. Contrôles exposition / EPI
   9. Propriétés physico-chimiques
   10. Stabilité et réactivité
   11. Toxicologie
   12. Écologie
   13. Élimination
   14. Transport (ADR/RID/IMDG)
   15. Réglementation (REACH, CLP)
   16. Autres informations
7. **Préparé par** et **Approuvé par (QA)**
8. **Fichier PDF** attaché
9. **Statut :** DRAFT → APPROVED → SUPERSEDED → WITHDRAWN

### 1.4 Génération PDF SDS

Chaque SDS a un PDF 16 sections auto-généré.

**Chemin :** Liste SDS → bouton **📄 PDF**

- Ouvre PDF nouvel onglet
- Format A4 ISO
- Contenu : 16 sections + préparé/approuvé + référence EC 2020/878
- Téléchargeable/imprimable

Ce PDF accompagne chaque livraison client.

### 1.5 Versioning SDS

Changement formule ou réglementation :
- Ancienne SDS : `SUPERSEDED`
- Nouvelle SDS : nouveau numéro (`v2`, `v3`)
- Unique : profil+version+langue

**Recommandation :** Revue annuelle. Remplir `next_review_date`.

---

## 2. DoP (Declaration of Performance)

### 2.1 Qu'est-ce que la DoP ?

**Déclaration de Performance** — Reg EU 305/2011 Annexe III, obligatoire pour marquage CE.

**Différence CoC vs. DoP :**
- **CoC :** délivrée par Notified Body (après audit)
- **DoP :** **déclarée par le fabricant** (avec sa signature)

Producteur algérien exportant vers l'UE → DoP obligatoire.

### 2.2 Liste DoP

**Chemin :** Menu gauche → **Conformité** → **DoP / Marquage CE**

URL directe : `/portal/uyum/dop/`

**Tableau :**
- N° DoP
- Produit
- Usage prévu
- v
- Date émission
- NB (numéro Notified Body)
- Badge statut (Émise/Brouillon)
- **Bouton 📄 CE PDF**

### 2.3 Nouvelle DoP

**Chemin :** Admin → `/admin/chemicals/declarationofperformance/add/`

1. **N° DoP :** Ex. `DOP-2026-001`
2. **Produit**
3. **CoC** (certificat NB lié)
4. **Version**
5. **Date émission**
6. **Usage prévu :** Ex. `Superplasticizer / High Range Water Reducer`
7. **Performance data (JSON) :** Valeurs tableau EN 934-2
   ```json
   {
     "chloride_ion_content": "<=0.1%",
     "alkali_content": "<=1.5%",
     "water_reduction": ">=12%",
     "compressive_strength_ratio_7d": ">=125%",
     "compressive_strength_ratio_28d": ">=115%"
   }
   ```
8. **Signataire :** Ex. `A. Bouzidi, Directeur Général`
9. **Statut :** DRAFT → ISSUED → SUPERSEDED → WITHDRAWN

### 2.4 Génération PDF DoP

**Chemin :** Liste DoP → bouton **📄 CE PDF**

PDF conforme Annexe III :
- Titre : **DECLARATION OF PERFORMANCE**
- N° DoP
- 10 sections :
  1. ID unique du produit
  2. Type/lot/série
  3. Usage prévu
  4. Fabricant (SARL MAPA Algérie + adresse)
  5. Représentant autorisé
  6. Système AVCP (System 2+)
  7. Norme harmonisée (EN 934-2:2009+A1:2012)
  8. Notified body
  9. **Tableau performance déclarée**
  10. Bloc signature

Ce PDF référencé sur emballage et documents client.

---

## 3. Notified Body et Audit FPC

### 3.1 Qu'est-ce qu'un Notified Body ?

Organisme indépendant qui audite le contrôle qualité usine pour marquage CE. NB européens reconnus par l'Algérie :
- **NB 1234 — CTC Groupe** (France)
- **NB 0987 — CSTB** (France)
- **NB 0432 — CATAS** (Italie)

### 3.2 Liste NB

**Chemin :** Admin → `/admin/chemicals/notifiedbody/`

Chaque NB : Numéro, Nom, Pays

### 3.3 Audits FPC (Factory Production Control)

Audit de contrôle qualité usine par le NB. EN 934-2 System 2+ → annuel/périodique.

### 3.4 Liste Audits FPC

**Chemin :** Menu gauche → **Conformité** → **Audit FPC (NB)**

URL directe : `/portal/uyum/fpc-audit/`

**Tableau :**
- N° Audit
- NB
- Type (INITIAL/SURVEILLANCE/SPECIAL/RENEWAL)
- Date
- Major NC (rouge)
- Minor NC (jaune)
- Observations
- **Résultat :**
  - 🟢 ✓ Conforme (PASSED)
  - 🔵 ✓ Avec constatations (PASSED_FINDINGS)
  - 🟠 Conditionnel (CONDITIONAL)
  - 🔴 ✗ Non conforme (FAILED)
- Cert délivré (✓/—)

### 3.5 Nouvel Audit FPC

**Chemin :** Admin → `/admin/chemicals/fpcaudit/add/`

1. **N° Audit :** Ex. `FPC-2026-001`
2. **Notified Body**
3. **Type audit**
4. **Date**
5. **Nom auditeur**
6. **Portée**
7. **Constatations**
8. **Nombres NC :** Major, Minor, Observations
9. **Résultat**
10. **Deadline actions correctives**
11. **Plan actions correctives**
12. **Rapport audit PDF**
13. **Certificat délivré**
14. **Prochain audit**

### 3.6 Préparation Audit

Checklist avant audit :
- ✅ Spécifications QCSpec approuvées QA
- ✅ Plans d'échantillonnage à jour (BR-QA-12)
- ✅ NCR tous fermés
- ✅ CAPA vérifiés efficacité
- ✅ Échantillons rétention conservés
- ✅ SDS + DoP à jour
- ✅ Étalonnages complets (CMMS)

---

## 4. CoC (Certificate of Conformity)

### 4.1 CoC vs. DoP

- **CoC :** document « assurance qualité production » du NB
- **DoP :** document « performance » signé par le fabricant

Pour marquage CE : d'abord CoC, puis DoP (référence CoC).

### 4.2 Enregistrement CoC

**Chemin :** Admin → `/admin/chemicals/certificateofconformity/`

1. **N° CoC**
2. **Produit**
3. **Plan test FPC** lié
4. **Norme :** `EN 934-2:2009+A1:2012`
5. **Type admixture :** Superplasticizer / HRWR / etc.
6. **Année marquage CE**
7. **N° DoP** (lien)
8. **Date émission + Validité**
9. **Organisme émetteur (NB)**
10. **Statut :** DRAFT/ISSUED/SUSPENDED/REVOKED
11. **Fichier PDF**

---

## 5. Suivi REACH SVHC

### 5.1 Qu'est-ce qu'une SVHC ?

**Substance of Very High Concern** — REACH. Exemples :
- Cancérigène
- Mutagène
- Toxique reproduction
- Persistant
- Bioaccumulatif

Concentration **> 0,1%** dans une MP → transmise au produit → notification downstream obligatoire.

### 5.2 Page Suivi SVHC

**Chemin :** Menu gauche → **Conformité** → **REACH SVHC**

URL directe : `/portal/uyum/reach-svhc/`

**Tableau (MP flaggées SVHC) :**
- Code, Nom
- **N° CAS** (ex. `9003-01-4`)
- **N° EC** (ex. `618-347-7`)
- **N° REACH Reg**
- **SVHC %**
- **Statut seuil :**
  - 🔴 **⚠ Notification requise** (> 0,1%)
  - 🟢 ✓ (≤ 0,1%)

**Bandeau alerte :** Si une MP > 0,1%, en haut :
`⚠ N MP au-dessus seuil 0,1% SVHC — notification downstream à préparer.`

### 5.3 Saisie Info SVHC

**Chemin :** Admin → détail RawMaterial

Champs :
- **SVHC flag :** True
- **SVHC % :** Ex. `0.150`
- **REACH Registration No** (format ECHA)
- **N° CAS**
- **N° EC**

Info depuis SDS fournisseur.

### 5.4 Notification Downstream

**REACH Article 33** : info au client si > 0,1% SVHC :
- Code produit
- Nom + CAS SVHC
- Concentration
- Info usage sûr

Actuellement manuel (auto ADMIX-ERP à venir).

---

## 6. Méthodes Test EN 480

### 6.1 Qu'est-ce que EN 480 ?

Série **EN 480** — standards tests additifs béton :
- EN 480-1 : Préparation échantillon
- EN 480-8 : Matière sèche %
- EN 480-10 : Ion chlorure
- EN 480-11 : Teneur air
- EN ISO 758 : Densité

### 6.2 Référence Méthode EN 480 sur Paramètre QC

**Chemin :** Admin → QCParameter → champ **en480_method_ref**

Exemples :
- Paramètre `CHLORIDE` → `EN 480-10 § 5.2`
- Paramètre `SOLIDS` → `EN 480-8 § 4.3`
- Paramètre `DENSITY` → `EN ISO 758`

Utilisé sur COA + audit FPC + questions spec client.

---

## 7. Échantillon de Rétention

Détail dans `05_stock.md` § 8.

**Aspect conformité :**
- Obligatoire pour chaque batch (EN 934-2)
- Durée de conservation : durée vie + 6 mois
- Source de ré-analyse en cas de réclamation/audit

---

## 8. Compatibilité Stockage

### 8.1 Zones Stockage

Voir `05_stock.md` § 7. Aspect conformité :

- Modèle **StorageZone** :
  - Classes de danger autorisées
  - Capacité max (kg)
  - Températures min/max
  - Type ventilation

- **StorageIncompatibility** — classes incompatibles :
  - Ex. Classe 3 (inflammable) + Classe 5.1 (oxydant) → risque explosion
  - Système alerte lors audit

### 8.2 Contrôle Stockage

Lors audit FPC/ISO, auditeurs inspectent magasin. Préparation :
- Vérifier bonne zone par MP
- Logs température prêts
- Test ventilation à jour
- MSDS (SDS) visible près de chaque MP

---

## 9. Conformité Algérie

### 9.1 SCF (Système Comptable Financier) — PCN 2010

Plan comptable algérien. ADMIX-ERP intégré :
- Classes 1-9
- Codes journal (JV, JA, JB, JC, JVE, JAE)
- Règles écritures

Détail : `02_comptabilite.md` § 6.

### 9.2 Déclaration TVA G50

Mensuel — TVA + acomptes IBS + autres taxes en une déclaration :
- Avant le 20 du mois à la DGI
- Modèle `TVADeclaration` prêt
- Calcul auto portal à venir

### 9.3 E-Facture DGI

Mandat e-facture reporté à 2027. ADMIX-ERP prêt :
- Champ pièce jointe facture
- Préparation JSON e-facture

### 9.4 Sonelgaz et Autres

- Électricité : facture Sonelgaz
- Eau : SEAAL
- Gaz : Sonelgaz

Ces factures traitées comme **factures de dépense** (`02_comptabilite.md` § 4).

---

## 10. FAQ

**Q : Revue annuelle SDS obligatoire ?**
R : EU 2020/878 § 4.1 → non obligatoire mais recommandée. Politique qualité entreprise = revue 6 mois ou annuelle.

**Q : CE marking sans DoP possible ?**
R : NON. EU 305/2011 CPR → DoP obligatoire. Même avec CoC NB, DoP fabricant obligatoire.

**Q : Major NC en audit FPC → certificat révoqué ?**
R : Dépend politique NB. Généralement `CONDITIONAL`, deadline actions correctives (60-90 jours). Sinon certificat suspendu.

**Q : Comment déterminer % SVHC ?**
R : Depuis SDS fournisseur. Si doute → tester en labo accrédité.

**Q : Référence méthode EN 480 obligatoire ?**
R : Demandée en audit FPC/ISO — bonne preuve. Ne pas laisser vide.

**Q : Retention 5 ans, puis-je détruire ?**
R : Durée vie + 6 mois = minimum. Politique entreprise peut être plus longue (contrats client 10 ans). Consulter directeur qualité.

**Q : Retrait d'une version SDS ?**
R : Statut `WITHDRAWN`. Clients peuvent avoir anciennes copies — notification officielle possible.

**Q : SDS en turc obligatoire ?**
R : Dépend — clients algériens : français suffit. Export Turquie → turc obligatoire.

---

## 11. Exercices Pratiques

1. **Nouvelle SDS :** `ADX-100` SDS français v1, 16 sections remplies, générer PDF
2. **DoP :** Même produit, performance_data JSON complet
3. **Audit FPC :** Nouvel audit SURVEILLANCE, résultat PASSED_FINDINGS
4. **REACH SVHC :** Saisir info SVHC pour une MP (>0,1% exemple)
5. **Comparaison PDF SDS :** Comparer deux versions côte à côte

Montrer au responsable conformité.
