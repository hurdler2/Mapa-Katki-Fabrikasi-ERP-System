# 01 — Connexion au Système et Interface

**Public :** Tous les employés
**Durée :** 30 minutes
**Prérequis :** Aucun — premier document à lire

---

## 1. Première Connexion au Système

### 1.1 Informations d'Accès

Votre administrateur système vous fournit :
- **Adresse web :** `http://erp.mapa.dz` ou `http://192.168.1.100:8000` (réseau interne)
- **Nom d'utilisateur :** Ex. `mohamed.belaidi` ou `ahmed.kaya`
- **Mot de passe temporaire :** À changer à la première connexion

### 1.2 Étapes de la Première Connexion

1. Ouvrez votre navigateur (Chrome, Firefox ou Edge recommandé)
2. Tapez l'URL de votre système dans la barre d'adresse
3. **L'écran de connexion** s'ouvre — entrez votre nom d'utilisateur et mot de passe
4. Cliquez sur **« Se connecter »**
5. À la première connexion, l'écran de changement de mot de passe apparaît — choisissez un **mot de passe fort** :
   - Au moins 8 caractères
   - Majuscule, minuscule, chiffre
   - Ex. `Mapa2026!`

### 1.3 Si Vous Oubliez Votre Mot de Passe

- Appelez le responsable informatique — il peut réinitialiser votre mot de passe
- **Ne partagez jamais** votre mot de passe avec qui que ce soit

---

## 2. Présentation de l'Interface

Après connexion, **l'écran d'accueil (Tableau de bord)** s'affiche. L'écran comporte trois zones principales :

```
┌─────────────────────────────────────────────────────────┐
│  ADMIX-ERP     Mohamed Belaidi · Comptable  [Déconnex.]│  ← BARRE SUPÉRIEURE
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  MENU    │           ZONE PRINCIPALE                    │
│  GAUCHE  │        (la page sélectionnée)                │
│          │                                              │
│  🏠 Accueil│                                              │
│  💰 Compta │                                              │
│  🏭 Prod.  │                                              │
│  🔬 Qualité│                                              │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 2.1 Barre Supérieure

- **À gauche :** Logo ADMIX-ERP (cliquez pour revenir à l'accueil)
- **À droite :** Votre nom + rôle + bouton **Déconnexion**
- **Notifications :** Si vous avez des approbations en attente, un badge apparaît

### 2.2 Menu Gauche

Vous voyez des menus différents selon votre rôle. Groupes principaux :

| Groupe | Contenu |
|--------|---------|
| **Accueil** | Tableau de bord, Approbations, Notifications |
| **Production** | Recettes, Ordres de production, Batches |
| **Qualité** | Spécifications, Échantillons, NCR |
| **Stock / Magasin** | Matières premières, Lots, Ajustement |
| **Ventes** | Clients, BL Client, Factures |
| **Achats** | Fournisseurs, Commandes |
| **Comptabilité** | Factures, Avances, Factures de dépense |
| **Conformité** | SDS, DoP, REACH, Audit FPC |
| **Rapports Direction** | BI Dashboard, Centre de Rapports |

**Note :** Si vous ne voyez pas certaines sections — vous n'avez pas les droits sur ce rôle. Contactez votre superviseur.

### 2.3 Zone Principale

C'est la zone où s'affiche la page/formulaire que vous avez sélectionné(e). Généralement trois parties :

- **Cartes KPI (en haut) :** Chiffres résumés — aujourd'hui / semaine / total
- **Barre de filtres :** Statut, date, catégorie
- **Tableau / formulaire principal :** Liste des enregistrements ou formulaire à remplir

---

## 3. Opérations Communes

Opérations de base répétées dans tous les modules :

### 3.1 Consulter la Liste des Enregistrements

Exemple : Page Factures → tous vos factures s'affichent en tableau.

- **Zone de recherche** (si disponible) : tapez un numéro ou nom
- **Boutons de filtre :** « Tous », « En attente d'approbation », « Payé »
- **Tri :** Cliquez sur les en-têtes de colonne pour trier

### 3.2 Ajouter un Nouvel Enregistrement

- Bouton bleu **« + Nouveau … »** en haut à droite
- Un formulaire vide s'ouvre — les champs obligatoires sont marqués `*`
- Terminez avec le bouton **Enregistrer**

### 3.3 Consulter / Modifier un Enregistrement

- Cliquez sur une ligne du tableau → la page de détail s'ouvre
- Bouton **Modifier** en haut à droite pour changer
- Si vous n'avez pas les droits, le bouton **Modifier** apparaît en gris

### 3.4 Joindre un Fichier

Vous pouvez joindre des fichiers à la plupart des formulaires (facture PDF, JPG certificat d'étalonnage, etc.) :

1. Cliquez sur le bouton **« Choisir un fichier »**
2. Sélectionnez PDF/JPG/PNG depuis votre ordinateur (max 10 Mo)
3. Après **Enregistrer**, le fichier est chargé automatiquement
4. Pour télécharger, cliquez sur le nom du fichier

### 3.5 Télécharger un Rapport / PDF

Vous pouvez télécharger factures, SDS, DoP en PDF :

- Bouton **« 📄 PDF »** en haut à droite de la page de détail
- Le document s'ouvre dans un nouvel onglet — vous pouvez le télécharger ou l'imprimer

---

## 4. Rôles et Permissions

Chaque utilisateur a un **rôle**. Le rôle détermine ce que vous pouvez voir et faire.

| Rôle | Ce qu'il peut faire |
|------|---------------------|
| **Comptable** | Facturation, encaissements, consultation cari |
| **Directeur Comptabilité** | Comptable + validation dépenses, clôture période |
| **Responsable Production** | Sélection recette, démarrage batch, ordre de production |
| **Qualité / QA** | Validation spécifications, ouverture NCR, gestion échantillons |
| **Responsable Magasin** | Réception marchandises, ajustement stock, expédition |
| **Représentant Commercial** | Enregistrement client, BL, suivi commande |
| **Achats** | Fournisseur, commande, réception marchandises |
| **Directeur Général** | Voit tout, accès rapports |

Si vous voyez **« Vous n'avez pas accès à cette page »** → allez voir votre superviseur, un rôle doit vous être attribué.

---

## 5. Format Numérique Algérien

Le système utilise le **format français/algérien** :

- ✅ Correct : `1.234.567,89 DZD` (point pour milliers, virgule pour décimales)
- ❌ Incorrect : `1,234,567.89` (format anglais — à ne pas utiliser)

**Attention :** Lors de la saisie d'une nouvelle facture, tapez les montants comme `1234.56` (comme Excel) ; le système affiche automatiquement `1.234,56`.

---

## 6. Raccourcis Fréquents

| Raccourci | Résultat |
|-----------|----------|
| Clic sur icône accueil | Retour au tableau de bord |
| **Déconnexion** en haut à droite | Fermer la session en toute sécurité |
| **F5** du navigateur | Rafraîchir la page |
| Clic droit → **Ouvrir dans un nouvel onglet** | Ouvrir dans un autre onglet |

---

## 7. Règles de Sécurité

**À faire :**
- ✅ **Fermez votre session** lorsque vous quittez votre poste (surtout au changement d'équipe)
- ✅ Changez votre mot de passe **tous les 6 mois**
- ✅ Signalez tout e-mail suspect à l'informatique

**À ne pas faire :**
- ❌ Ne donnez votre mot de passe à personne (même à la direction)
- ❌ N'écrivez pas votre mot de passe sur un papier laissé sur le bureau
- ❌ Ne laissez pas la session ouverte si quelqu'un d'autre utilise l'ordinateur

---

## 8. En Cas de Problème

**Étape 1 — Essayez de résoudre vous-même :**
- Rafraîchissez la page (F5)
- Essayez un autre navigateur
- Fermez la session et reconnectez-vous

**Étape 2 — Premier niveau de support :**
- Demandez au propriétaire du module (comptabilité → directeur comptabilité)
- Relisez la section concernée de ce document

**Étape 3 — Deuxième niveau :**
- Appelez le responsable informatique : [TÉLÉPHONE]
- Envoyez un e-mail : [MAIL]
- Joignez une capture d'écran avec l'erreur (résolution plus rapide)

---

## 9. Prochaine Étape

Lisez le document du module correspondant à votre rôle :

- Comptable → `02_comptabilite.md`
- Production → `03_production.md`
- Qualité → `04_qualite.md`
- Magasin → `05_stock.md` *(en préparation)*
- Ventes → `06_ventes.md` *(en préparation)*
