import React, { useState } from 'react';
import './FeedbackForm.css';

const FeedbackForm = ({ sentiment, onSubmitFeedback }) => {
  const [rating, setRating] = useState(0);
  const [textFeedback, setTextFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const startTime = useState(Date.now())[0];

  const handleSubmit = async () => {
    const interactionTime = (Date.now() - startTime) / 1000; // Convert to seconds
    
    try {
      await onSubmitFeedback({
        rating,
        textFeedback,
        interactionTime,
        correct: rating >= 3 // Consider ratings of 3 or higher as "correct"
      });
      setSubmitted(true);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  if (submitted) {
    return (
      <div className="feedback-success">
        <h3>Thank you for your feedback! 🎉</h3>
        <p>Your input helps us improve our sentiment analysis.</p>
      </div>
    );
  }

  return (
    <div className="enhanced-feedback">
      <h3>How accurate was our sentiment analysis?</h3>
      
      <div className="sentiment-display">
        <div className={`sentiment-result ${sentiment.sentiment ? 'positive' : 'negative'}`}>
          <span className="sentiment-emoji">{sentiment.sentiment ? '😊' : '😞'}</span>
          <span className="sentiment-text">{sentiment.sentiment ? 'Positive' : 'Negative'}</span>
          {sentiment.confidence && (
            <div className="confidence-bar">
              <div 
                className="confidence-fill" 
                style={{ width: `${sentiment.confidence * 100}%` }}
              />
              <span className="confidence-text">
                {(sentiment.confidence * 100).toFixed(0)}% confident
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="star-rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            className={`star ${rating >= star ? 'active' : ''}`}
            onClick={() => setRating(star)}
            aria-label={`Rate ${star} stars`}
          >
            ★
          </button>
        ))}
      </div>
      
      <textarea
        className="feedback-text"
        value={textFeedback}
        onChange={(e) => setTextFeedback(e.target.value)}
        placeholder="Would you like to tell us more about why you gave this rating? (Optional)"
        rows={3}
      />
      
      <button 
        className="submit-feedback" 
        onClick={handleSubmit}
        disabled={rating === 0}
      >
        Submit Feedback
      </button>
    </div>
  );
};

export default FeedbackForm; 