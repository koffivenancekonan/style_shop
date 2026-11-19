-- Mise à jour étape 3 : procédure de lecture du reçu (à importer UNE fois dans phpMyAdmin > Importer).
SET NAMES utf8mb4;
USE style_shop_db;
DROP PROCEDURE IF EXISTS lire_recu;
DELIMITER //
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
GRANT EXECUTE ON PROCEDURE style_shop_db.lire_recu TO 'style_vendeur'@'localhost';
FLUSH PRIVILEGES;
