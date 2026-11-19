-- STYLE SHOP PORT-BOUËT : schéma MySQL/MariaDB (XAMPP)
-- Import : phpMyAdmin > onglet "Importer" > choisir ce fichier > Exécuter.
-- IMPORTANT : changez les deux mots de passe MySQL plus bas (et le .env).
SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS style_shop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE style_shop_db;

CREATE TABLE IF NOT EXISTS utilisateurs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nom_utilisateur VARCHAR(50) NOT NULL UNIQUE,
  mot_de_passe_hash VARCHAR(100) NOT NULL,
  role ENUM('admin','gestionnaire') NOT NULL,
  actif TINYINT(1) NOT NULL DEFAULT 1,
  doit_changer_mdp TINYINT(1) NOT NULL DEFAULT 1,
  cree_le DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS articles (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nom VARCHAR(120) NOT NULL,
  categorie VARCHAR(60) NOT NULL,
  taille VARCHAR(20) NOT NULL,
  couleur VARCHAR(40) NOT NULL,
  marque VARCHAR(60) NOT NULL,
  prix_achat_min INT UNSIGNED NOT NULL,
  prix_achat_max INT UNSIGNED NOT NULL,
  prix_achat_reel INT UNSIGNED NOT NULL,
  prix_vente INT UNSIGNED NOT NULL,
  quantite_stock INT UNSIGNED NOT NULL DEFAULT 0,
  actif TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT chk_articles_prix CHECK (prix_achat_min <= prix_achat_reel AND prix_achat_reel <= prix_achat_max),
  CONSTRAINT chk_articles_positifs CHECK (prix_vente >= 0 AND quantite_stock >= 0),
  INDEX idx_articles_nom (nom),
  INDEX idx_articles_categorie (categorie)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ventes (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  date_heure DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total INT UNSIGNED NOT NULL DEFAULT 0,
  nb_articles INT UNSIGNED NOT NULL DEFAULT 0,
  utilisateur_id INT UNSIGNED NOT NULL,
  CONSTRAINT fk_ventes_utilisateur FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
  INDEX idx_ventes_date (date_heure)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lignes_vente (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  vente_id INT UNSIGNED NOT NULL,
  article_id INT UNSIGNED NOT NULL,
  quantite INT UNSIGNED NOT NULL,
  prix_vente_unitaire INT UNSIGNED NOT NULL,
  prix_achat_unitaire INT UNSIGNED NOT NULL,
  CONSTRAINT chk_lignes_qte CHECK (quantite > 0),
  CONSTRAINT fk_lignes_vente FOREIGN KEY (vente_id) REFERENCES ventes(id),
  CONSTRAINT fk_lignes_article FOREIGN KEY (article_id) REFERENCES articles(id),
  INDEX idx_lignes_vente (vente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS parametres (
  cle VARCHAR(50) PRIMARY KEY,
  valeur VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO parametres (cle, valeur) VALUES ('seuil_stock_faible', '5'), ('theme', 'clair');

-- Vues : le vendeur ne voit JAMAIS les colonnes d'achat
CREATE OR REPLACE VIEW vue_articles_vendeur AS
  SELECT id, nom, categorie, taille, couleur, marque, prix_vente, quantite_stock
  FROM articles WHERE actif = 1;

CREATE OR REPLACE VIEW vue_parametres_vendeur AS
  SELECT cle, valeur FROM parametres WHERE cle IN ('seuil_stock_faible');

DROP PROCEDURE IF EXISTS obtenir_utilisateur;
DROP PROCEDURE IF EXISTS changer_mot_de_passe;
DROP PROCEDURE IF EXISTS creer_vente;
DROP PROCEDURE IF EXISTS ajouter_ligne_vente;
DROP PROCEDURE IF EXISTS finaliser_vente;
DROP PROCEDURE IF EXISTS lire_recu;
DELIMITER //

CREATE PROCEDURE obtenir_utilisateur(IN p_nom VARCHAR(50))
SQL SECURITY DEFINER
BEGIN
  SELECT id, nom_utilisateur, mot_de_passe_hash, role, actif, doit_changer_mdp
  FROM utilisateurs WHERE nom_utilisateur = p_nom;
END //

-- Le changement n'est accepté que si l'ancien hash correspond
CREATE PROCEDURE changer_mot_de_passe(IN p_id INT UNSIGNED, IN p_ancien VARCHAR(100), IN p_nouveau VARCHAR(100))
SQL SECURITY DEFINER
BEGIN
  UPDATE utilisateurs SET mot_de_passe_hash = p_nouveau, doit_changer_mdp = 0
  WHERE id = p_id AND mot_de_passe_hash = p_ancien AND actif = 1;
  SELECT ROW_COUNT() AS modifie;
END //

-- Une vente = START TRANSACTION (application) + creer_vente + N x ajouter_ligne_vente + finaliser_vente + COMMIT
CREATE PROCEDURE creer_vente(IN p_utilisateur INT UNSIGNED, OUT p_vente_id INT UNSIGNED)
SQL SECURITY DEFINER
BEGIN
  INSERT INTO ventes (date_heure, total, nb_articles, utilisateur_id) VALUES (NOW(), 0, 0, p_utilisateur);
  SET p_vente_id = LAST_INSERT_ID();
END //

CREATE PROCEDURE ajouter_ligne_vente(IN p_vente INT UNSIGNED, IN p_article INT UNSIGNED, IN p_qte INT UNSIGNED)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_stock INT UNSIGNED; DECLARE v_pv INT UNSIGNED; DECLARE v_pa INT UNSIGNED; DECLARE v_actif TINYINT;
  IF p_qte IS NULL OR p_qte < 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Quantité invalide';
  END IF;
  SELECT quantite_stock, prix_vente, prix_achat_reel, actif INTO v_stock, v_pv, v_pa, v_actif
  FROM articles WHERE id = p_article FOR UPDATE;
  IF v_actif IS NULL OR v_actif = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Article introuvable ou archivé';
  END IF;
  IF v_stock < p_qte THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock insuffisant';
  END IF;
  UPDATE articles SET quantite_stock = quantite_stock - p_qte WHERE id = p_article;
  INSERT INTO lignes_vente (vente_id, article_id, quantite, prix_vente_unitaire, prix_achat_unitaire)
  VALUES (p_vente, p_article, p_qte, v_pv, v_pa);
END //

CREATE PROCEDURE finaliser_vente(IN p_vente INT UNSIGNED)
SQL SECURITY DEFINER
BEGIN
  UPDATE ventes SET
    total = (SELECT COALESCE(SUM(quantite * prix_vente_unitaire), 0) FROM lignes_vente WHERE vente_id = p_vente),
    nb_articles = (SELECT COALESCE(SUM(quantite), 0) FROM lignes_vente WHERE vente_id = p_vente)
  WHERE id = p_vente;
END //

CREATE PROCEDURE lire_recu(IN p_vente INT UNSIGNED)
SQL SECURITY DEFINER
BEGIN
  SELECT v.date_heure, v.total, v.nb_articles, a.nom, a.taille, a.couleur,
         l.quantite, l.prix_vente_unitaire AS prix_unitaire
  FROM ventes v
  JOIN lignes_vente l ON l.vente_id = v.id
  JOIN articles a ON a.id = l.article_id
  WHERE v.id = p_vente ORDER BY l.id;
END //
DELIMITER ;

-- Utilisateurs MySQL (CHANGEZ LES MOTS DE PASSE, puis reportez-les dans .env)
CREATE USER IF NOT EXISTS 'style_admin'@'localhost' IDENTIFIED BY 'ChangezMoi_Admin_2025';
CREATE USER IF NOT EXISTS 'style_vendeur'@'localhost' IDENTIFIED BY 'ChangezMoi_Vendeur_2025';
GRANT ALL PRIVILEGES ON style_shop_db.* TO 'style_admin'@'localhost';
GRANT SELECT ON style_shop_db.vue_articles_vendeur TO 'style_vendeur'@'localhost';
GRANT SELECT ON style_shop_db.vue_parametres_vendeur TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.obtenir_utilisateur TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.changer_mot_de_passe TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.creer_vente TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.ajouter_ligne_vente TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.finaliser_vente TO 'style_vendeur'@'localhost';
GRANT EXECUTE ON PROCEDURE style_shop_db.lire_recu TO 'style_vendeur'@'localhost';
FLUSH PRIVILEGES;
