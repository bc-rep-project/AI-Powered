import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Embedding, Dense, Concatenate

class NeuralRecommender(Model):
    def __init__(self, num_users: int, num_items: int, embedding_dim: int):
        super().__init__()
        
        # Embeddings
        self.user_embedding = Embedding(
            num_users + 1,  # Add 1 for padding/unknown
            embedding_dim,
            name="user_embedding"
        )
        self.item_embedding = Embedding(
            num_items + 1,  # Add 1 for padding/unknown
            embedding_dim,
            name="item_embedding"
        )
        
        # Layers
        self.concat = Concatenate(axis=1)
        self.dense_1 = Dense(128, activation='relu')
        self.dense_2 = Dense(64, activation='relu')
        self.output_layer = Dense(1, activation='sigmoid')

    def call(self, inputs):
        """Forward pass of the model"""
        # Get inputs
        user_input = inputs["user_input"]
        item_input = inputs["item_input"]
        
        # Get embeddings
        user_embedded = self.user_embedding(user_input)
        item_embedded = self.item_embedding(item_input)
        
        # Concatenate embeddings
        concat = self.concat([user_embedded, item_embedded])
        
        # Dense layers
        x = self.dense_1(concat)
        x = self.dense_2(x)
        
        # Output
        return self.output_layer(x)

    def build_graph(self):
        """Build the model graph"""
        user_input = tf.keras.Input(shape=(), dtype=tf.float32, name="user_input")
        item_input = tf.keras.Input(shape=(), dtype=tf.float32, name="item_input")
        
        return Model(
            inputs={"user_input": user_input, "item_input": item_input},
            outputs=self.call({"user_input": user_input, "item_input": item_input})
        ) 