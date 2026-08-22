# 99 — FAQ Générales

Ce document couvre les questions inter-modules. Questions spécifiques dans les documents module concernés.

---

## Accès Système et Utilisateur

**Q : J'ai oublié mon mot de passe, que faire ?**
R : Contactez le responsable IT. Ne partagez jamais par e-mail. Après reset, un mot de passe temporaire est fourni, à changer à la première connexion.

**Q : Quel navigateur pour le système ?**
R : Chrome, Firefox, Edge (2 dernières versions). Safari limité. Internet Explorer non supporté.

**Q : Connexion mobile possible ?**
R : Oui — design responsive. Mais pour formulaires complexes (facturation), PC/tablette recommandé.

**Q : Même compte sur 2 PC simultanés ?**
R : Techniquement possible mais déconseillé. Audit trail peut se mélanger. Créer un compte séparé.

**Q : Système lent, que faire ?**
R :
1. Ctrl+F5 hard refresh
2. Vider cache navigateur (Ctrl+Shift+Del)
3. Essayer autre navigateur
4. Signaler à IT (si lenteur à horaires précis)

**Q : Tout est en français mais je veux le turc ?**
R : Paramètres langue navigateur :
- Chrome → Paramètres → Langue → Ajouter Turc et mettre en priorité
- Puis rafraîchir

Système bilingue — s'adapte automatiquement.

---

## Droits et Rôles

**Q : Erreur « Vous n'avez pas accès » ?**
R : Rôle sans accès. Contacter superviseur. Ex. comptable sans accès production par défaut.

**Q : Rôle changé mais anciens droits visibles ?**
R : Fermer session et reconnecter. Cache Django rafraîchit.

**Q : Donner un rôle à un utilisateur (admin) ?**
R : Admin → `/admin/auth/user/` → utilisateur → Groups → ajouter le groupe.

**Q : Désactiver temporairement un utilisateur ?**
R : Admin → User → décocher **is_active**. Préférable à supprimer (audit trail).

---

## Saisie de Données et Format

**Q : Comment saisir les nombres : 1234.56 ou 1.234,56 ?**
R : **En saisie** : point (comme Excel) `1234.56`. Système affiche `1.234,56`.

**Q : Format de date ?**
R : Champs date HTML5 → picker calendrier. Manuel : `YYYY-MM-DD` (ex. `2026-08-22`).

**Q : Retour à la ligne dans un texte ?**
R : TextField (multi-ligne) : Entrée. CharField : impossible.

**Q : Caractères spéciaux (turc/arabe/français) ?**
R : Système UTF-8 — turc (ğ, ş, ı, ö, ü, ç), arabe, français accentué (é, à, ç) fonctionnent.

**Q : Erreur en chargeant PDF/JPG ?**
R :
- Taille max : 10 MB
- Formats : PDF, JPG, PNG (extension correcte)
- Nom suspect (caractères, espaces) → renommer

---

## Facture et Document

**Q : Modifier une facture après émission ?**
R : Uniquement en **DRAFT**. Après POSTED : impossible — nécessite avoir ou écriture inverse.

**Q : PDF mal formaté à l'impression ?**
R : Imprimer en PDF (Ctrl+P → cible : PDF). Firefox meilleur rendu.

**Q : Sauter un numéro de facture ?**
R : Non — loi algérienne (DGI) : numérotation continue sans trou. Système auto-génère.

**Q : Plusieurs copies d'un document ?**
R : PDF multi-copies (imprimer + photocopier). Chaque document unique dans le système.

---

## Paiement et Compte Courant

**Q : Paiement enregistré mais facture toujours 'DRAFT' ?**
R : Facture doit d'abord passer à **POSTED** (période ouverte). Puis paiement accepté.

**Q : Chèque sans provision ?**
R : Payment → `check_status` = `BOUNCED`, `check_bounce_reason`. Facture → `PARTIALLY_PAID`.

**Q : Avance à un client, allouer à un autre ?**
R : Non — avance uniquement au propre client. Sinon rembourser et ré-enregistrer.

**Q : Solde compte client négatif ?**
R : Signifie créditeur — client a trop payé ou avance versée. Vérifier et corriger.

---

## Production et Qualité

**Q : Batch lancé mais bouton « Démarrer » introuvable ?**
R : Sur page détail ordre, sous le tableau besoins théoriques. Non visible : stock insuffisant ou statut invalide.

**Q : Batch SCADA n'arrive pas, production ?**
R : Lancer batch manuel (admin → ProductionBatch → add). Signaler problème SCADA à IT/intégrateur.

**Q : Batch RELEASED puis REJECT possible ?**
R : Techniquement oui mais audit trail complexe. Ouvrir NCR, décision directeur qualité, puis changer statut. Raison obligatoire.

**Q : Test FAIL mais batch RELEASED ?**
R : QCTestResult et statut batch séparés — lien manuel. QA doit passer batch en QC_HOLD, puis REJECTED. Règle : chaque FAIL → batch REJECTED (sauf jugement d'ingénieur).

**Q : PDF SDS très long (10+ pages), raccourcir ?**
R : SDS 16 sections légalement obligatoires. Section vide → système affiche "[not filled]". Écrire au minimum "N/A" — plus propre.

---

## Conformité

**Q : Vendre en Algérie sans DoP ?**
R : Non obligatoire en Algérie. Mais export UE → DoP + marquage CE + CoC obligatoires.

**Q : Enregistrement REACH pour producteur algérien ?**
R : Production+vente Algérie : non. Export UE : Only Representative (OR) ou importateur enregistré.

**Q : Échec audit FPC, révocation ?**
R : Selon politique NB et sévérité NC. Généralement `CONDITIONAL`, 60-90 jours actions correctives. Sinon `SUSPENDED`, puis `REVOKED`.

**Q : Mise à jour SDS chaque année ?**
R : Non légalement obligatoire mais recommandé. Suivre `next_review_date`. Formule/loi change → **immédiat** nouvelle version.

---

## Rapport et Analyse

**Q : Rapport Excel téléchargeable ?**
R : Limité. Certaines listes admin ont export. Rapports portal : capture écran + Ctrl+P (PDF). Export Excel à venir.

**Q : Snapshot fin mois ?**
R : Manuel — imprimer PDF et archiver chaque fin de mois. Auto à venir.

**Q : Pourquoi KPI différents à différents endroits ?**
R : Chaque rapport peut utiliser période différente (jour / mois / 30 jours). Lire définition.

**Q : Relevé compte client incorrect ?**
R : Causes possibles :
- Facture non POSTED (reste DRAFT)
- Paiement au mauvais client
- Enregistrement avance manquant

Signaler IT + comptabilité.

---

## Sauvegarde et Sécurité

**Q : Données sauvegardées ?**
R : Oui — IT effectue sauvegarde automatique quotidienne. Données critiques : vérifier avec IT.

**Q : Suppression accidentelle, récupération ?**
R : Dépend. Certains (Invoice, Payment, StockMovement) non supprimables (audit trail) — passent en "CANCELLED". D'autres suppressibles admin mais irrécupérables. Contacter IT (restauration sauvegarde possible).

**Q : Protection données personnelles ?**
R : Conforme KVKK/RGPD. Mot de passe haché, invisible. Même IT ne voit pas (peut juste reset).

---

## Mise à Jour et Maintenance

**Q : Système mis à jour, interface différente ?**
R : Normal. Notes de release expliquent. IT doit informer. Problème → signaler.

**Q : Nouvelle fonctionnalité, comment demander ?**
R : E-mail au responsable IT. Suggérer :
- Décrire problème actuel
- Expliquer fonctionnalité souhaitée
- Cas d'usage

**Q : Quand maintenance système ?**
R : Weekend / nuit — IT annonce. 15 min maintenance critique normale.

---

## Divers

**Q : Notification mise à jour de ce document ?**
R : IT / qualité envoie e-mail. Documents (`personel_egitimi/`) versionnés — vérifier date de dernière mise à jour.

**Q : Formation insuffisante, complément ?**
R : Signaler à responsable module + directeur qualité. Recyclage 1-2/an standard.

**Q : Temps pour apprendre le système ?**
R : Par rôle :
- 1ère semaine : document rôle + pratique (10-15h)
- 1er mois : apprendre par le faire
- 3 mois : maîtrise confortable

**Q : Empêcher captures écran ?**
R : Windows Snip & Sketch ou similaire. Système ne surveille pas.

---

## Aide Urgente

**Problème critique ?** (production arrêtée, facturation impossible, erreur critique)

1. **5 min :** Rafraîchir, fermer/rouvrir session
2. **10 min suivantes :** Autre navigateur, e-mail IT
3. **Persiste ?** Ligne urgente : **[TÉLÉPHONE_URGENCE]**

Erreur détaillée : capture écran + message d'erreur + action en cours → IT.

---

**Version document :** 1.0
**Dernière mise à jour :** 22 août 2026
