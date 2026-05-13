
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

# Gerando dados sintéticos (Clusters de exemplo)
n = 300
c1 = np.random.randn(n, 3) + [2, 2, 2]
c2 = np.random.randn(n, 3) + [-2, -2, -2]
coords = np.vstack([c1, c2])
labels = np.array([1]*n + [0]*n)
preds = np.random.uniform(0.8, 1.0, n).tolist() + np.random.uniform(0, 0.2, n).tolist()

# Criando a figura do Plotly
fig = go.Figure(data=[go.Scatter3d(
    x=coords[:,0], y=coords[:,1], z=coords[:,2],
    mode='markers',
    marker=dict(size=5, color=preds, colorscale='RdBu_r', opacity=0.8, showscale=True),
    text=[f"Clase: {'Fuego' if l==1 else 'No-fuego'}<br>Pred: {p:.2%}" for l, p in zip(labels, preds)]
)])

fig.update_layout(
    title="PROVA DE CONCEITO: Auditoría t-SNE 3D",
    margin=dict(l=0, r=0, b=0, t=40),
    scene=dict(xaxis_title='t-SNE 1', yaxis_title='t-SNE 2', zaxis_title='t-SNE 3'),
    template="plotly_dark"
)

# Salvando como HTML (mesmo método do projeto)
html_content = fig.to_html(include_plotlyjs='cdn', full_html=True)
with open("test_tsne.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML de teste gerado com sucesso!")
