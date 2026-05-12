def recluster_notes(notes):
    """
    notes: list of dicts with keys id, title, content
    returns:
      dict { note_id: cluster_id }
    """
    # 1. build texts
    texts = [
        note["title"] + " " + note["content"]
        for note in notes
    ]

    # 2. TF-IDF
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )
    X = vectorizer.fit_transform(texts)

    # 3. DBSCAN
    from sklearn.cluster import DBSCAN
    dbscan = DBSCAN(
        eps=0.95,
        min_samples=2,
        metric="cosine"
    )
    labels = dbscan.fit_predict(X)

    # 4. Generate Cluster Names
    cluster_names = {}
    
    import numpy as np
    
    # Get feature names (words)
    feature_names = vectorizer.get_feature_names_out()
    
    unique_labels = set(labels)
    for label in unique_labels:
        if label == -1:
            continue
            
        # Get indices of notes in this cluster
        indices = np.where(labels == label)[0]
        
        # Calculate mean TF-IDF vector for the cluster
        cluster_center = X[indices].mean(axis=0).A1  # A1 flattens matrix
        
        # Get top 2 terms
        top_indices = cluster_center.argsort()[::-1][:2]
        top_terms = [feature_names[i] for i in top_indices]
        
        # Formulate name (Capitalize)
        name = " ".join([t.capitalize() for t in top_terms])
        cluster_names[label] = name

    # 5. return mapping
    cluster_map = {}
    for i in range(len(notes)):
        note_id = notes[i]["id"]
        cluster_id = int(labels[i])
        
        if cluster_id == -1:
             cluster_map[note_id] = "General" # Keep -1 as General
        else:
             # Use the generated name
             cluster_map[note_id] = cluster_names.get(cluster_id, "Cluster")

    return cluster_map