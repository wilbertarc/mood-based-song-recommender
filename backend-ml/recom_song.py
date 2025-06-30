#!/usr/bin/env python
# coding: utf-8

# In[1]:


# get_ipython().run_line_magic('pip', 'install pandas numpy scikit-learn sentence-transformers faiss-cpu gradio python-dotenv')
# get_ipython().run_line_magic('pip', 'install transformers torch')


# In[2]:


# get_ipython().run_line_magic('pip', 'install spotipy')


# In[3]:


import os
import re
import numpy as np
import pandas as pd
from tqdm.auto import tqdm
from sklearn.preprocessing import MinMaxScaler
from sentence_transformers import SentenceTransformer
import faiss
import gradio as gr
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

USE_SPOTIFY = False

POC_SAMPLE = None

SPOTIPY_CLIENT_ID     = "512c40be42074ea2aeccb7dc9b548c53"
SPOTIPY_CLIENT_SECRET = "e4df0c601ac74a609fc39101c0688347"

if USE_SPOTIFY:
    os.environ["512c40be42074ea2aeccb7dc9b548c53"]     = SPOTIPY_CLIENT_ID
    os.environ["e4df0c601ac74a609fc39101c0688347"] = SPOTIPY_CLIENT_SECRET
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        name = sp.track("3n3Ppam7vgaVa1iaRUc9Lp")["name"]
        print(f"✅ Spotify auth OK — Sample track: {name}")
    except Exception as e:
        print("❌ Spotify auth failed:", e)
else:
    print("⚠️ Skipping Spotify use (dummy audio features).")


# In[4]:


CSV_PATH = "songs.csv"

# 1) Read with Python engine and skip any bad lines
try:
    df = pd.read_csv(
        CSV_PATH,
        encoding="utf-8",
        engine="python",      # more tolerant parser
        on_bad_lines="skip",  # drop malformed rows
        sep=","               # explicit delimiter
    )
    print(f"✅ Raw load succeeded: {len(df):,} rows × {df.shape[1]} cols")
except Exception as e:
    print("❌ Error loading CSV:", e)
    raise

# 2) (Optional) Quick column check
print("Columns:", df.columns.tolist())

# 3) Apply POC sampling if configured
if POC_SAMPLE:
    before = len(df)
    df = df.sample(min(POC_SAMPLE, len(df)), random_state=42).reset_index(drop=True)
    print(f"🔬 Sampled down from {before:,} to {len(df):,} rows for quicker testing")

# 4) Show the first few rows
df.head(3)


# In[5]:


# Rename for consistency
df = df.rename(columns={
    "song": "name",
    "text": "lyrics",
    "link": "orig_link"
})
print("After rename:", df.columns.tolist())

if USE_SPOTIFY:

    cache = {}
    def lookup_id(name, artist):
        key = (name, artist)
        if key in cache: return cache[key]
        q = f'track:"{name}" artist:"{artist}"'
        try:
            items = sp.search(q=q, type="track", limit=1).get("tracks", {}).get("items", [])
            cid = items[0]["id"] if items else None
        except Exception:
            cid = None
        cache[key] = cid
        return cid

    df["spotify_id"] = [
        lookup_id(row.name, row.artist) for row in tqdm(df.itertuples(index=False),
                                                        total=len(df),
                                                        desc="Looking up IDs")
    ]
    valid = df["spotify_id"].notna().sum()
    print(f"🔍 Found {valid:,}/{len(df):,} Spotify IDs")
    df = df[df["spotify_id"].notna()].reset_index(drop=True)
else:

    df["spotify_id"] = [f"dummy_{i}" for i in range(len(df))]
print(f"➡️ {len(df):,} tracks after ID step")


# In[6]:


# drop duplicates
df.drop_duplicates(subset="spotify_id", inplace=True)
df.dropna(subset=["lyrics"], inplace=True)
print(f"➡️ {len(df):,} tracks after dropping dupes/missing")

# clean
def clean_text(txt):
    s = str(txt).lower()
    s = re.sub(r"\[.*?\]", "", s)        # remove "[Chorus]", etc.
    s = re.sub(r"[^a-z0-9\s]", " ", s)   # remove punctuations
    return re.sub(r"\s+", " ", s).strip()

df["lyrics_clean"] = df["lyrics"].map(clean_text)
df = df[df["lyrics_clean"] != ""].reset_index(drop=True)
print(f"➡️ {len(df):,} tracks after cleaning")


# In[7]:


if USE_SPOTIFY:
    audio_feats = []
    for i in tqdm(range(0, len(df), 50), desc="Fetching audio"):
        batch = df["spotify_id"].iloc[i:i+50].tolist()
        try:
            feats = sp.audio_features(batch)
            audio_feats.extend([f for f in feats if f and f.get("id")])
        except Exception as e:
            print(f"  ⚠️ Batch {i} error:", e)

    if not audio_feats:
        print("⚠️ No features fetched—falling back to zeros")
        df[["valence","energy","danceability"]] = 0.0
    else:
        df_af = (pd.DataFrame(audio_feats)
                   .rename(columns={"id":"spotify_id"})
                   [["spotify_id","valence","energy","danceability"]])
        df = df.merge(df_af, on="spotify_id", how="inner")
        print(f"✅ Merged audio: {len(df):,} tracks")
        scaler = MinMaxScaler()
        df[["valence","energy","danceability"]] = scaler.fit_transform(
            df[["valence","energy","danceability"]]
        )
else:
    df["valence"]      = 0.5
    df["energy"]       = 0.5
    df["danceability"] = 0.5
    print("⚠️ Used dummy audio features (0.5)")


# In[8]:


assert len(df) > 0, "❌ No tracks to embed – check earlier steps!"

encoder = SentenceTransformer("all-MiniLM-L6-v2")
emb_list = []
for i in tqdm(range(0, len(df), 64), desc="Embedding lyrics"):
    texts = df["lyrics_clean"].iloc[i:i+64].tolist()
    emb_list.extend(encoder.encode(texts))

assert len(emb_list) == len(df), "❌ Embedding count mismatch!"
df["lyr_emb"] = emb_list
print("✨ Embeddings computed")


# In[9]:


emb_matrix = np.vstack(df["lyr_emb"].values).astype("float32")
faiss.normalize_L2(emb_matrix)

index = faiss.IndexFlatIP(emb_matrix.shape[1])
index.add(emb_matrix)
print(f"🔍 FAISS index built with {index.ntotal:,} vectors")

faiss.write_index(index, "lyric_index.faiss")


# In[10]:


def recommend(diary, top_k=50, rec_n=10, alpha=0.7):
    
    q = clean_text(diary)
    q_emb = encoder.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)

    D, I = index.search(q_emb, top_k)
    cands = df.iloc[I[0]].copy().reset_index(drop=True)

    mood_sim = cands[["valence","energy","danceability"]].mean(axis=1)
    cands["score"] = alpha * D[0] + (1 - alpha) * mood_sim

    recs = (
        cands
        .sort_values("score", ascending=False)
        .drop_duplicates("artist")
        .head(rec_n)
    )

    return recs[["spotify_id","name","artist","score"]]


# In[11]:


# ── Evaluation: Classification Report ──

# from sklearn.metrics import classification_report

# # 1) Define your train & test sets:
# #    Each is a list of (diary_text, true_spotify_id)

# train_df = pd.read_csv("train_data.csv")
# test_df = pd.read_csv("test_data.csv")

# # train_data = [
# #     ("I felt so happy after acing my exam",    "3n3Ppam7vgaVa1iaRUc9Lp"),
# #     ("It’s raining and I'm feeling blue today","0VjIjW4GlUZAMYd2vXMi3b"),
# #     # … add more train examples …
# # ]
# # test_data = [
# #     ("Worked out and am full of energy!",      "7ouMYWpwJ422jRcDASZB7P"),
# #     ("Missing my friends, feeling lonely",     "1lDWb6b6ieDQ2xT7ewTC3G"),
# #     # … add more test examples …
# # ]

# # Training evaluation
# y_train_true, y_train_pred = [], []
# for _, row in train_df.iterrows():
#     recs = recommend(row["diary"], top_k=50, rec_n=10, alpha=0.7)
#     rec_ids = recs["spotify_id"].tolist()
#     y_train_true.append(1)
#     y_train_pred.append(1 if row["spotify_id"] in rec_ids else 0)

# # Testing evaluation
# y_test_true, y_test_pred = [], []
# for _, row in test_df.iterrows():
#     recs = recommend(row["diary"], top_k=50, rec_n=10, alpha=0.7)
#     rec_ids = recs["spotify_id"].tolist()
#     y_test_true.append(1)
#     y_test_pred.append(1 if row["spotify_id"] in rec_ids else 0)

# # 4) Print classification reports, focusing on class “1 = relevant”
# print("Train :")
# print(classification_report(
#     y_train_true, y_train_pred,
#     labels=[1], target_names=["relevant"],
#     digits=2
# ))

# print("Test :")
# print(classification_report(
#     y_test_true, y_test_pred,
#     labels=[1], target_names=["relevant"],
#     digits=2
# ))


# In[12]:


# import gradio as gr

# def gradio_recs(diary_text, num_recs):
#     out = recommend(diary_text, rec_n=num_recs)
#     out = out.rename(columns={
#         "name": "🎵 Title",
#         "artist": "🎤 Artist",
#         "score": "✨ Match Score"
#     })
#     return out

# with gr.Blocks(title="AI Song Recommender") as demo:
#     gr.Markdown(
#         """
#         # 🎶 Mood-Based Song Recommender
#         _Powered by AI + Spotify + Lyrics Embeddings_

#         Just describe how your day went, and this AI will find songs that match your mood.
#         """
#     )

#     with gr.Row():
#         with gr.Column():
#             diary_input = gr.Textbox(
#                 label="📝 What's on your mind today?",
#                 placeholder="e.g., I feel happy and energetic after hanging out with friends!",
#                 lines=6
#             )
#             num_songs = gr.Slider(1, 15, value=5, step=1, label="🎯 Number of Songs to Recommend")
#             submit_btn = gr.Button("🎧 Recommend Songs")

#         with gr.Column():
#             result_table = gr.Dataframe(headers=["🎵 Title", "🎤 Artist", "✨ Match Score"])

#     submit_btn.click(fn=gradio_recs, inputs=[diary_input, num_songs], outputs=result_table)

# demo.launch(share=True)


# In[13]:


# get_ipython().run_line_magic('pip', 'install pickle')


# In[ ]:





# In[15]:


# from sentence_transformers import SentenceTransformer

# embedder = SentenceTransformer('paraphrase-mpnet-base-v2')
# print("✅ Upgraded embedding model loaded.")


# In[16]:


# AUDIO_FEATURES = [
#     "acousticness", "danceability", "energy", "instrumentalness",
#     "liveness", "loudness", "speechiness", "tempo", "valence"
# ]

# def get_audio_features(track_id):
#     try:
#         features = sp.audio_features(track_id)[0]
#         if features:
#             return [features[feat] for feat in AUDIO_FEATURES]
#     except Exception as e:
#         print(f"⚠️ Audio feature error for {track_id}: {e}")
#     return [0.0] * len(AUDIO_FEATURES)

# df[AUDIO_FEATURES] = df["spotify_id"].apply(lambda x: pd.Series(get_audio_features(x)))
# print("✅ Added Spotify audio features.")


# In[17]:


# lyrics_embeddings = embedder.encode(df["lyrics"].tolist(), show_progress_bar=True)

# scaler = MinMaxScaler()
# audio_scaled = scaler.fit_transform(df[AUDIO_FEATURES])

# combined_embeddings = np.hstack([lyrics_embeddings, audio_scaled])
# print("✅ Combined lyric and audio features for similarity search.")


# # In[ ]:


# dim = combined_embeddings.shape[1]
# index = faiss.IndexFlatL2(dim)
# index.add(combined_embeddings)
# print(f"✅ FAISS index built with {dim}-dimensional vectors.")

