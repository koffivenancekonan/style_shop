-- Données de démo : une vingtaine d'articles (montants en FCFA)
SET NAMES utf8mb4;
USE style_shop_db;
INSERT INTO articles (nom, categorie, taille, couleur, marque, prix_achat_min, prix_achat_max, prix_achat_reel, prix_vente, quantite_stock) VALUES
('T-shirt coton col rond', 'T-shirt', 'M', 'Blanc', 'Local', 2500, 3500, 3000, 6000, 25),
('T-shirt coton col rond', 'T-shirt', 'L', 'Noir', 'Local', 2500, 3500, 3000, 6000, 18),
('T-shirt polo', 'T-shirt', 'L', 'Bleu marine', 'Lacoste', 8000, 12000, 10000, 18000, 10),
('T-shirt imprimé', 'T-shirt', 'S', 'Gris', 'Puma', 3500, 5500, 4500, 9000, 4),
('Jean slim', 'Jean', '40', 'Bleu', 'Levi''s', 9000, 13000, 11000, 20000, 12),
('Jean droit', 'Jean', '42', 'Noir', 'Zara', 8000, 12000, 10000, 18000, 8),
('Jean déchiré', 'Jean', '38', 'Bleu clair', 'Local', 6000, 9000, 7500, 14000, 3),
('Bermuda cargo', 'Bermuda', 'M', 'Kaki', 'Local', 4000, 6000, 5000, 10000, 15),
('Bermuda jean', 'Bermuda', 'L', 'Bleu', 'Levi''s', 6000, 9000, 7500, 14000, 9),
('Bermuda sport', 'Bermuda', 'M', 'Noir', 'Adidas', 5000, 7500, 6000, 12000, 0),
('Body manches longues', 'Body', 'S', 'Blanc', 'Local', 3000, 5000, 4000, 8000, 14),
('Body dentelle', 'Body', 'M', 'Noir', 'Local', 3500, 5500, 4500, 9000, 6),
('Body col roulé', 'Body', 'L', 'Beige', 'Zara', 4000, 6000, 5000, 10000, 2),
('Baskets running', 'Chaussure', '42', 'Blanc', 'Nike', 18000, 26000, 22000, 38000, 7),
('Baskets montantes', 'Chaussure', '43', 'Noir', 'Adidas', 20000, 28000, 24000, 42000, 5),
('Sandales cuir', 'Chaussure', '41', 'Marron', 'Local', 5000, 8000, 6500, 12000, 11),
('Mocassins', 'Chaussure', '44', 'Noir', 'Local', 9000, 13000, 11000, 20000, 1),
('Casquette', 'Accessoire', 'Unique', 'Noir', 'Nike', 2500, 4500, 3500, 7000, 20),
('Ceinture cuir', 'Accessoire', '105', 'Marron', 'Local', 3000, 5000, 4000, 8000, 13),
('Lunettes de soleil', 'Accessoire', 'Unique', 'Noir', 'Local', 2000, 4000, 3000, 6000, 16);
-- Les 2 comptes de démo (admin_demo, vendeur_demo) se créent avec : python scripts/creer_comptes_demo.py
