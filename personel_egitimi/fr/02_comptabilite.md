# 02 — Module Comptabilité

**Public :** Comptables, directeur comptabilité, responsable finance
**Durée :** 90 minutes
**Prérequis :** `01_introduction.md` lu

Ce document couvre l'ensemble du module Comptabilité :
1. Émission de Facture (Ventes / Achats)
2. Enregistrement Paiement (Chèque / Virement / Espèces)
3. Avance Client (§23) et Allocation
4. Factures de Dépense
5. Consultation Compte Client (Relevé)
6. Balance et Clôture de Période
7. Rapports

---

## 1. Émission de Facture

### 1.1 Nouvelle Facture de Vente (AR)

**Chemin :** Menu gauche → **Comptabilité** → **Nouvelle Facture**

1. Saisissez le **N° Facture** — le système suggère `INV-2026-001`
2. **Type Facture :** Sélectionnez `Vente (AR)`
3. **Date Facture :** Aujourd'hui (par défaut) ou choisir
4. **Date d'Échéance :** Optionnel ; généralement 30 jours plus tard
5. Choisissez le **Client** dans la liste déroulante
   - **Important :** Si un **escompte** est défini pour ce client, il est chargé automatiquement
   - Ex. si C002 GICA Groupe a `15%` défini, le champ « Taux d'escompte » devient `15,00`
6. **Ligne de Facture :**
   - Description : ex. `Superplasticizer ADX-100 · 5000 kg`
   - Quantité : `5000`
   - Prix Unitaire (HT) : `120,00` (DZD)
   - Taux TVA : `TVA 19` (défaut algérien)
7. **Pièce Jointe (optionnel) :** Facture originale PDF/JPG
8. **Notes :** Texte libre
9. Cliquez sur **Enregistrer la Facture (Brouillon)**

La facture est créée en état **DRAFT (Brouillon)** — une validation séparée est requise pour la comptabiliser.

### 1.2 Facture d'Achat (AP)

Même flux, sauf :
- **Type Facture :** Sélectionnez `Achat (AP)`
- Le champ **Client** est masqué, le champ **Fournisseur** apparaît — sélectionnez-y
- La pièce jointe est généralement l'original du fournisseur (pour notification DGI)

### 1.3 Note de Crédit (Avoir)

Pour retour client ou correction :
- **Type Facture :** `Avoir - vente`
- Autres champs identiques ; le montant est comptabilisé en négatif

### 1.4 PDF de la Facture

1. Depuis la liste des factures, cliquez sur la facture
2. Cliquez sur le bouton **📄 PDF** en haut à droite
3. La facture s'ouvre en format A4 dans un nouvel onglet :
   - Logo de l'entreprise + adresse complète
   - Numéros NIF, NIS, RC, article import (obligation algérienne)
   - Encadrés Émetteur / Facturé à
   - Tableau des lignes (en-tête bleu)
   - Encadré total (HT + TVA + TTC + escompte)
   - Informations banque/RIB
   - Ligne de signature + pied de page légal
4. **Imprimer** (Ctrl+P) ou **Télécharger PDF**

---

## 2. Enregistrement Paiement

### 2.1 Paiement en Espèces ou par Virement

**Chemin :** Sur la page de détail de la facture → bouton **Nouveau Paiement**

1. Sélectionnez la **Méthode** dans la liste :
   - `Espèces (Nakit)`
   - `Virement / EFT (Havale)`
   - `Chèque (Çek)`
   - `Crédoc (Akreditif)`
   - `Carte CIB`
2. **Direction :** `Encaissement (du client)` ou `Décaissement (au fournisseur)`
3. Saisissez la **Date** et le **Montant**

### 2.2 Paiement par Virement (Spécifique)

Quand `Virement / EFT` est sélectionné, un panneau supplémentaire s'ouvre :
- **Banque de Transfert :** Choisir parmi 13 banques algériennes : BEA, BNA, CPA, BADR, BDL, CNEP, AGB, SGA, BNP, FRB, TRUST, HOUSING, Autre
- **IBAN** (RIB algérien 24 chiffres)
- **Date du Transfert**

### 2.3 Paiement par Chèque (Spécifique — Fréquent en Algérie)

Quand `Chèque` est sélectionné, un panneau détaillé s'ouvre :
- **Banque du Chèque :** Parmi les 13 banques
- **N° Chèque**
- **Date d'Émission**
- **Date d'Échéance** (chèques post-datés fréquents)
- **Statut du Chèque :** Reçu / Remis à la banque / Sans provision (bounced)
- **Nom du Tireur** (titulaire du compte émetteur)
- **Image du Chèque** (photo/scan — optionnel)

### 2.4 Statut de la Facture Après Paiement

Après enregistrement du paiement, la facture est mise à jour automatiquement :
- Montant total payé → `PAID (Payé)`
- Paiement partiel → `PARTIALLY_PAID`
- Avant paiement → `DRAFT` ou `POSTED`

---

## 3. Avance Client et Allocation (§23)

Si le client a effectué un paiement anticipé avant l'émission de la facture, il est enregistré comme avance.

### 3.1 Nouvel Enregistrement d'Avance

**Chemin :** Menu gauche → **Avances Client** → **+ Nouvelle Avance**

Alternatif : Interface admin → `/admin/accounting/customeradvance/add/`

1. **N° Avance :** ex. `ADV-2026-001`
2. **Client :** sélectionner dans la liste
3. **Date**
4. **Montant** (TTC)
5. **Méthode :** Virement / Chèque / Espèces
6. **Référence Document :** N° virement, n° chèque ou n° reçu
7. **Enregistrer**

L'avance est créée en état **OPEN (Ouvert)**.

### 3.2 Allocation de l'Avance à une Facture

Après l'émission d'une facture, vous voulez lier l'avance à cette facture :

1. Allez à la liste **Avances Client**
2. Cliquez sur le bouton **« Allouer »** à côté de l'avance
3. Dans le formulaire :
   - Sélectionnez la **Facture** (les factures du même client sont listées)
   - Saisissez le **Montant à Allouer** (maximum : reste de l'avance)
4. Cliquez sur **Allouer**

Le système automatiquement :
- Augmente le champ `amount_paid` de la facture
- Passe la facture à `PAID` si totalement payée
- Passe l'avance à `FULLY_ALLOCATED` si totalement épuisée

### 3.3 Fractionnement de l'Avance (Plusieurs Factures)

Une avance peut être fractionnée entre plusieurs factures :
- Avance : 150.000 DZD
- Facture 1 : 80.000 DZD → allouer 80.000 DZD
- Facture 2 : 50.000 DZD → allouer 50.000 DZD
- Reste de l'avance : 20.000 DZD (en attente d'une nouvelle facture)

---

## 4. Factures de Dépense

Les charges d'exploitation (maintenance, loyer, conseil, électricité) sont documentées **séparément**.

### 4.1 Nouvelle Facture de Dépense

**Chemin :** Menu gauche → **Factures de Dépense** → **+ Nouvelle Facture de Dépense**

1. **Fournisseur :** Société de maintenance, consultant, bailleur
2. **Catégorie :** 11 choix
   - Réparation / Maintenance
   - Électricité / Eau / Gaz
   - Loyer
   - Conseil / Étude
   - Transport / Carburant
   - Nettoyage / Hygiène
   - Sécurité
   - Bureau / Papeterie
   - Juridique / Fiscal
   - Marketing / Publicité
   - Autre
3. **Date Facture** et **Date d'Échéance**
4. **Facture N° du Fournisseur :** N° du document du fournisseur
5. **Détails / Récapitulatif :** Description du travail (ex. « Remplacement pompe réacteur R-101 »)
6. **Référence Équipement / Lieu :** Pour quel équipement/emplacement
7. Saisissez le **Montant HT** et le **Taux TVA**
   - La TVA est calculée automatiquement
   - Le TTC est mis à jour automatiquement
8. **Justificatif :** PDF/JPG (obligation légale algérienne — l'original doit être conservé)
9. **Enregistrer (Brouillon)**

### 4.2 Flux d'Approbation Facture de Dépense

Une nouvelle facture est créée en état **DRAFT**. L'approbation est requise pour le paiement :

1. **DRAFT** → Comptable clique **« Soumettre pour Approbation »** → **SUBMITTED**
2. **SUBMITTED** → Directeur consulte le détail, clique **✓ Approuver** ou **✗ Rejeter**
3. **APPROVED** → Après paiement, cliquer **« 💳 Marquer comme Payé »** + saisir la référence → **PAID**

### 4.3 Qui a Quels Droits

- **Comptable :** Création de brouillon + soumission pour approbation
- **Directeur Comptabilité :** Approbation + rejet + marquage payé
- **Directeur Général :** Toutes les opérations + modification

---

## 5. Consultation Compte Client (Relevé)

Voir toutes les factures, paiements et avances d'un client sur un seul écran.

### 5.1 Comment Ouvrir le Compte Client

**Chemin :** Menu gauche → **Rapports** → **Échéancier Clients** → bouton **Détail** sur la ligne du client

Alternatif : URL directe `/portal/muhasebe/cari/<client_id>/`

### 5.2 Contenu de la Page

**4 Cartes KPI :**
- Total Factures (TTC)
- Total Paiements
- Avance Ouverte
- **Solde** — nous sommes créanciers ou soldés ?

**Tableau Factures :**
- N° facture, date, TTC, payé, restant, statut

**Tableau Avances :**
- N° avance, date, montant, alloué, restant, statut

---

## 6. Balance et Clôture de Période

### 6.1 Balance (Trial Balance)

**Chemin :** Menu gauche → **Balance**

Selon le SCF algérien (PCN 2010) :
- **1 :** Capitaux propres
- **2 :** Immobilisations
- **3 :** Stocks
- **4 :** Créances/Dettes
- **5 :** Trésorerie
- **6 :** Charges
- **7 :** Produits

Pour chaque compte :
- Débit
- Crédit
- Solde

### 6.2 Détail du Compte (Ledger)

Pour voir les mouvements d'un compte :
- Cliquez sur le numéro de compte dans le tableau
- Toutes les écritures de journal sont listées (date, description, débit, crédit)

### 6.3 Clôture Mensuelle

À la fin du mois :
1. Toutes les factures de dépense doivent être **APPROVED**
2. Toutes les factures de vente doivent être **POSTED**
3. Le directeur comptabilité clôture la période : `/admin/accounting/period/`
4. En état **CLOSED**, plus aucune facture ne peut être émise
5. Préparation déclaration G50 — à remettre à la DGI avant le 20 du mois

---

## 7. Rapports

### 7.1 Tableau de Bord Comptabilité

**Chemin :** Menu gauche → **Tableau de Bord Comptabilité**

- 8 cartes KPI (revenu du jour, créances ouvertes, etc.)
- 6 graphiques Chart.js (tendance mensuelle, types de paiement, aging, etc.)
- 2 tableaux (chèques à venir, factures en retard)

### 7.2 Échéancier Clients (Aging)

**Chemin :** Menu gauche → **Rapports** → **Échéancier Clients**

- Tranches d'âge : 0-30, 31-60, 61-90, 90+ jours
- Total des créances ouvertes
- Répartition par client
- Bouton **Détail** pour chaque client → compte client

### 7.3 Échéancier Fournisseurs

Même logique, mais côté fournisseur.

---

## 8. FAQ

**Q : J'ai émis une facture mais l'escompte n'est pas venu automatiquement, que faire ?**
R : Le champ `default_discount_pct` sur la fiche client est vide. Ouvrez la fiche client et saisissez le taux d'escompte (`/admin/masterdata/customer/`), puis émettez à nouveau la facture.

**Q : J'ai enregistré un paiement au mauvais client, puis-je le supprimer ?**
R : La suppression directe est impossible (audit trail). Vous devez saisir une écriture inverse (paiement négatif). Informez le directeur comptabilité.

**Q : Un chèque est revenu sans provision, comment le traiter ?**
R : Allez sur l'enregistrement Payment → mettez `check_status` à `BOUNCED` + remplissez `check_bounce_reason`. La facture retourne automatiquement à `PARTIALLY_PAID`.

**Q : J'ai approuvé une facture de dépense mais je veux la supprimer ?**
R : Une facture approuvée ne peut être supprimée. Contactez le directeur comptabilité ; il peut saisir une écriture inverse (note de crédit).

**Q : Erreur en essayant d'allouer une avance à une facture d'un autre client ?**
R : Comportement correct. Une avance ne peut être allouée qu'à une facture **du même client**. Si vous avez sélectionné le mauvais client, **annulez**.

**Q : Le format numérique s'affiche avec des points au lieu du format algérien ?**
R : Vérifiez les paramètres de langue de votre navigateur. Chrome → Paramètres → Langue → doit être **Français (Algérie)**.

---

## 9. Exercices Pratiques

À la fin de la formation, réalisez ces 5 exemples :

1. **Nouvelle facture :** 3 lignes, 2 produits différents, TVA 19%, escompte 10%
2. **Paiement :** Paiement de la facture ci-dessus fractionné 60% chèque + 40% virement
3. **Avance :** Nouvelle avance client de 100.000 DZD en espèces
4. **Facture de dépense :** Facture de maintenance MECATECH (Réparation Machine)
5. **Compte client :** Consulter le compte d'un client + faire une capture d'écran

Une fois chaque exercice terminé, montrez au formateur.
