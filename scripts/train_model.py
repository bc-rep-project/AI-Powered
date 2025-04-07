#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers
import argparse
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecommendationModel:
    def __init__(self, embedding_dim=32):
        self.embedding_dim = embedding_dim
        self.user_encoder = None
        self.content_encoder = None
        self.model = None
        self.history = None
    
    def _build_model(self, num_users, num_content_items):
        """Build a neural collaborative filtering model"""
        # Input layers
        user_input = layers.Input(shape=(1,), name='user_input')
        content_input = layers.Input(shape=(1,), name='content_input')
        
        # Embedding layers
        user_embedding = layers.Embedding(
            input_dim=num_users + 1,  # Add one for unknown users
            output_dim=self.embedding_dim,
            name='user_embedding'
        )(user_input)
        
        content_embedding = layers.Embedding(
            input_dim=num_content_items + 1,  # Add one for unknown content
            output_dim=self.embedding_dim,
            name='content_embedding'
        )(content_input)
        
        # Flatten embeddings
        user_vector = layers.Flatten()(user_embedding)
        content_vector = layers.Flatten()(content_embedding)
        
        # Concatenate embeddings
        concat = layers.Concatenate()([user_vector, content_vector])
        
        # Dense layers
        dense1 = layers.Dense(64, activation='relu')(concat)
        dropout1 = layers.Dropout(0.2)(dense1)
        dense2 = layers.Dense(32, activation='relu')(dropout1)
        dropout2 = layers.Dropout(0.2)(dense2)
        
        # Output layer
        output = layers.Dense(1)(dropout2)
        
        # Create model
        model = tf.keras.Model(
            inputs=[user_input, content_input],
            outputs=output
        )
        
        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(0.001),
            loss='mse',
            metrics=['mae']
        )
        
        self.model = model
        return model
    
    def train(self, interactions_df, epochs=10, batch_size=64, validation_split=0.2):
        """Train the recommendation model"""
        # Encode user and content IDs
        self.user_encoder = LabelEncoder()
        self.content_encoder = LabelEncoder()
        
        user_ids = self.user_encoder.fit_transform(interactions_df['user_id'].values)
        content_ids = self.content_encoder.fit_transform(interactions_df['content_id'].values)
        ratings = interactions_df['value'].values
        
        # Create train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            np.column_stack((user_ids, content_ids)),
            ratings,
            test_size=validation_split,
            random_state=42
        )
        
        # Build model
        num_users = len(self.user_encoder.classes_)
        num_content_items = len(self.content_encoder.classes_)
        logger.info(f"Building model with {num_users} users and {num_content_items} content items")
        self._build_model(num_users, num_content_items)
        
        # Train model
        logger.info(f"Training model for {epochs} epochs with batch size {batch_size}")
        self.history = self.model.fit(
            [X_train[:, 0], X_train[:, 1]],
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=([X_test[:, 0], X_test[:, 1]], y_test),
            verbose=1
        )
        
        # Evaluate model
        loss, mae = self.model.evaluate([X_test[:, 0], X_test[:, 1]], y_test)
        logger.info(f"Model evaluation - Loss: {loss:.4f}, MAE: {mae:.4f}")
        
        return self.history
    
    def get_recommendations(self, user_id, content_ids=None, top_k=10):
        """Get recommendations for a user"""
        if self.model is None:
            raise ValueError("Model has not been trained")
        
        try:
            # Encode user ID
            user_encoded = self.user_encoder.transform([user_id])[0]
        except:
            logger.warning(f"User {user_id} not in training data, using fallback")
            user_encoded = 0  # Use first user as fallback
        
        # If content_ids is not provided, use all content items
        if content_ids is None:
            content_encoded = np.arange(len(self.content_encoder.classes_))
        else:
            try:
                # Filter for content IDs that exist in the encoder
                valid_content_ids = []
                valid_encoded_ids = []
                
                for cid in content_ids:
                    try:
                        encoded = self.content_encoder.transform([cid])[0]
                        valid_content_ids.append(cid)
                        valid_encoded_ids.append(encoded)
                    except:
                        continue
                
                if not valid_content_ids:
                    logger.warning("No valid content IDs provided, using all content")
                    content_encoded = np.arange(len(self.content_encoder.classes_))
                    content_ids = self.content_encoder.classes_
                else:
                    content_encoded = np.array(valid_encoded_ids)
                    content_ids = valid_content_ids
            except:
                logger.warning("Error encoding content IDs, using all content")
                content_encoded = np.arange(len(self.content_encoder.classes_))
                content_ids = self.content_encoder.classes_
        
        # Create input arrays
        user_array = np.array([user_encoded] * len(content_encoded))
        
        # Get predictions
        predictions = self.model.predict([user_array, content_encoded]).flatten()
        
        # Sort by prediction score and get top-k
        top_indices = np.argsort(predictions)[-top_k:][::-1]
        
        # Convert back to original IDs and create result list
        results = []
        for idx in top_indices:
            content_id = content_ids[idx] if isinstance(content_ids, list) else self.content_encoder.inverse_transform([content_encoded[idx]])[0]
            results.append((content_id, float(predictions[idx])))
        
        return results
    
    def save(self, model_path):
        """Save the model and encoders"""
        if self.model is None:
            raise ValueError("Model has not been trained")
        
        # Create directory if it doesn't exist
        os.makedirs(model_path, exist_ok=True)
        
        # Save model
        self.model.save(os.path.join(model_path, 'model'))
        
        # Save encoders
        np.save(os.path.join(model_path, 'user_classes.npy'), self.user_encoder.classes_)
        np.save(os.path.join(model_path, 'content_classes.npy'), self.content_encoder.classes_)
        
        # Save model info
        model_info = {
            'embedding_dim': self.embedding_dim,
            'num_users': len(self.user_encoder.classes_),
            'num_content_items': len(self.content_encoder.classes_),
            'saved_at': datetime.now().isoformat()
        }
        
        with open(os.path.join(model_path, 'model_info.json'), 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
    
    @classmethod
    def load(cls, model_path):
        """Load the model and encoders"""
        # Load model info
        with open(os.path.join(model_path, 'model_info.json'), 'r') as f:
            model_info = json.load(f)
        
        # Create instance
        instance = cls(embedding_dim=model_info['embedding_dim'])
        
        # Load model
        instance.model = tf.keras.models.load_model(os.path.join(model_path, 'model'))
        
        # Load encoders
        user_classes = np.load(os.path.join(model_path, 'user_classes.npy'), allow_pickle=True)
        content_classes = np.load(os.path.join(model_path, 'content_classes.npy'), allow_pickle=True)
        
        instance.user_encoder = LabelEncoder()
        instance.user_encoder.classes_ = user_classes
        
        instance.content_encoder = LabelEncoder()
        instance.content_encoder.classes_ = content_classes
        
        logger.info(f"Model loaded from {model_path}")
        logger.info(f"Model info: {model_info}")
        
        return instance
    
    def plot_history(self, save_path=None):
        """Plot training history"""
        if self.history is None:
            raise ValueError("Model has not been trained")
        
        plt.figure(figsize=(12, 4))
        
        # Plot loss
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['loss'], label='Training Loss')
        plt.plot(self.history.history['val_loss'], label='Validation Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        # Plot MAE
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['mae'], label='Training MAE')
        plt.plot(self.history.history['val_mae'], label='Validation MAE')
        plt.title('Model MAE')
        plt.xlabel('Epoch')
        plt.ylabel('MAE')
        plt.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Training history plot saved to {save_path}")
        else:
            plt.show()

def load_interactions(data_path):
    """Load interaction data from JSON file"""
    with open(os.path.join(data_path, 'interactions.json'), 'r') as f:
        interactions = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(interactions)
    
    return df

def main():
    parser = argparse.ArgumentParser(description='Train recommendation model')
    parser.add_argument('--data-dir', type=str, default='data/processed/movielens-small',
                        help='Directory containing processed data')
    parser.add_argument('--sample', action='store_true',
                        help='Use sample data instead of full dataset')
    parser.add_argument('--model-dir', type=str, default='models',
                        help='Directory to save the model')
    parser.add_argument('--embedding-dim', type=int, default=32,
                        help='Embedding dimension')
    parser.add_argument('--epochs', type=int, default=10,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Batch size for training')
    args = parser.parse_args()
    
    # Create model directory
    model_path = os.path.join(args.model_dir, f"recommender_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(model_path, exist_ok=True)
    
    # Determine data path
    data_path = os.path.join(args.data_dir, 'sample' if args.sample else '')
    logger.info(f"Loading data from {data_path}")
    
    # Load interaction data
    interactions_df = load_interactions(data_path)
    logger.info(f"Loaded {len(interactions_df)} interactions")
    
    # Train model
    model = RecommendationModel(embedding_dim=args.embedding_dim)
    history = model.train(
        interactions_df,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
    
    # Save model
    model.save(model_path)
    
    # Plot and save training history
    model.plot_history(save_path=os.path.join(model_path, 'training_history.png'))
    
    # Test recommendations
    test_users = interactions_df['user_id'].unique()[:5]  # Take 5 random users for testing
    
    for user_id in test_users:
        recommendations = model.get_recommendations(user_id, top_k=5)
        logger.info(f"Top 5 recommendations for user {user_id}:")
        for content_id, score in recommendations:
            logger.info(f"  Content ID: {content_id}, Score: {score:.4f}")

if __name__ == "__main__":
    main() 