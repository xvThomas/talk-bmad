# Modèles OpenRouter disponibles

## DeepSeek-V3.2 (`openrouter-deepseek-v3`)

**Caractéristiques techniques:**
- **ID OpenRouter**: `deepseek/deepseek-v3.2`
- **Contexte**: 106,496 tokens
- **Sortie max**: 8,192 tokens
- **Prix**: $0.14/M input, $0.28/M output
- **Tool use**: ✅ Support function calling
- **Thinking**: ❌ Pas de support thinking effort

**Points forts:**
- Excellent en raisonnement et tâches complexes
- Bon en français et multilingue
- Meilleur rapport qualité/prix actuel
- Idéal pour agents avec outils MCP

**Cas d'usage recommandé:**
- Agents intelligents avec outils (ign-nav, owm)
- Tâches nécessitant un raisonnement poussé
- Conversations longues avec contexte étendu

---

## DeepSeek-4.1-Flash (`openrouter-deepseek-flash`)

**Caractéristiques techniques:**
- **ID OpenRouter**: `deepseek/deepseek-4.1-flash`
- **Contexte**: 128,000 tokens
- **Sortie max**: 8,192 tokens
- **Prix**: $0.10/M input, $0.10/M output (prix fixe)
- **Tool use**: ✅ Support function calling
- **Thinking**: ❌ Pas de support thinking effort

**Points forts:**
- Très économique (prix fixe input/output)
- Rapide ("flash" dans le nom)
- Contexte 128K étendu
- Bon pour tâches quotidiennes

**Cas d'usage recommandé:**
- Tâches économiques avec outils simples
- Conversations longues à faible coût
- Quand la vitesse est importante

---

## DeepSeek-Chat (`openrouter-deepseek-chat`)

**Caractéristiques techniques:**
- **ID OpenRouter**: `openrouter/deepseek/deepseek-chat`
- **Contexte**: 128,000 tokens
- **Sortie max**: 16,384 tokens
- **Prix**: Variable selon le modèle sous-jacent
- **Tool use**: ✅ Support function calling
- **Thinking**: ❌ Pas de support thinking effort

**Points forts:**
- Contexte et sortie max étendus
- Routage automatique vers le meilleur modèle DeepSeek disponible
- Bon équilibre pour usage général

**Cas d'usage recommandé:**
- Usage général quand on ne sait pas quel modèle choisir
- Quand on a besoin de 16K tokens de sortie
- Routage automatique vers le modèle optimal

---

## Configuration requise

Pour utiliser ces modèles, il faut:
1. Une clé API OpenRouter (`OPENROUTER_API_KEY`)
2. Activer le provider OpenRouter dans le backend
3. Sélectionner le modèle dans l'interface frontend

**Note sur le tool use:** Tous les modèles DeepSeek supportent le function calling, ce qui les rend parfaits pour les agents utilisant les serveurs MCP `ign-nav` et `owm`.
