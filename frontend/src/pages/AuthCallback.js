import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Beer } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { updateUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    // Check for error passed in query string from backend
    const error = searchParams.get('error');
    if (error) {
      const messages = {
        unauthorized_domain: 'Only @5dm.africa email addresses are allowed.',
        google_auth_denied: 'Google sign-in was cancelled.',
        invalid_state: 'Security check failed. Please try again.',
      };
      navigate('/', { replace: true, state: { error: messages[error] || 'Authentication failed.' } });
      return;
    }

    // Backend has already set the session cookie — just fetch the user
    const fetchUser = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
        const userData = response.data;
        updateUser(userData);

        if (!userData.phone || !userData.accepted_terms) {
          navigate('/profile-setup', { replace: true });
        } else {
          navigate('/dashboard', { replace: true });
        }
      } catch (err) {
        console.error('Auth callback error:', err);
        const errorMessage = err.response?.data?.detail || 'Authentication failed';
        navigate('/', { replace: true, state: { error: errorMessage } });
      }
    };

    fetchUser();
  }, [navigate, searchParams, updateUser]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-hh-green border-2 border-black shadow-brutal rounded-lg flex items-center justify-center mx-auto mb-4 animate-pulse">
          <Beer className="w-8 h-8 text-black" />
        </div>
        <p className="font-display text-xl uppercase tracking-wide">Authenticating...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
