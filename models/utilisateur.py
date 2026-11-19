from dataclasses import dataclass, field


@dataclass
class Utilisateur:
    id: int
    nom_utilisateur: str
    role: str  # 'admin' ou 'gestionnaire'
    doit_changer_mdp: bool
    mot_de_passe_hash: str = field(default="", repr=False)  # jamais affiché

    @property
    def est_admin(self) -> bool:
        return self.role == "admin"
