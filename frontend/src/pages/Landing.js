import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Beer, ArrowRight, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const ENABLE_DEV_AUTH = process.env.REACT_APP_ENABLE_DEV_AUTH === 'true';

const Landing = () => {
  const { login } = useAuth();
  const location = useLocation();
  const errorMessage = location.state?.error;
  const [devUsers, setDevUsers] = useState([]);
  const [devUsersLoading, setDevUsersLoading] = useState(false);

  useEffect(() => {
    if (!ENABLE_DEV_AUTH) {
      return;
    }

    const fetchDevUsers = async () => {
      setDevUsersLoading(true);
      try {
        const response = await axios.get(`${API}/dev/users`);
        setDevUsers(response.data || []);
      } catch (error) {
        setDevUsers([]);
      } finally {
        setDevUsersLoading(false);
      }
    };

    fetchDevUsers();
  }, []);

  const getDevUserLabel = (devUser) => {
    if (devUser.role === 'super_admin') return 'Local Super Admin';
    if (devUser.role === 'admin') return 'Local Admin';
    return 'Local Customer';
  };

  const loginAsDevUser = (email) => {
    window.location.href = `${BACKEND_URL}/api/dev/login?email=${encodeURIComponent(email)}`;
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
            <Beer className="w-6 h-6 text-hh-green" />
          </div>
          <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-black">
            HH Jaba
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Hero Image */}
          <div className="relative mb-8">
            <img
              src="https://customer-assets.emergentagent.com/job_jaba-admin-hub/artifacts/f9epea1o_5%20tastes.jpg"
              alt="Happy Hour Jaba - All Flavors"
              className="w-full h-72 object-cover border-2 border-black shadow-brutal rounded-lg"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent rounded-lg flex items-end p-4">
              <p className="text-white font-display text-xl uppercase">
                5DM Staff Portal
              </p>
            </div>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <Alert variant="destructive" className="mb-6 border-2 border-black shadow-brutal-sm">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {/* Welcome Text */}
          <div className="text-center mb-8">
            <h2 className="font-display text-3xl font-bold uppercase tracking-tight mb-2">
              Happy Hour Jaba
            </h2>
            <p className="text-gray-600 font-body">
              Order your favorite flavored beers with ease. 
              Credit or M-Pesa – your choice.
            </p>
          </div>

          {/* Features - All 6 Flavors */}
          <div className="grid grid-cols-3 gap-2 mb-8">
            <div className="bg-flavor-tamarind/10 border-2 border-flavor-tamarind p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-tamarind rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Tamarind</span>
            </div>
            <div className="bg-flavor-watermelon/10 border-2 border-flavor-watermelon p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-watermelon rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Watermelon</span>
            </div>
            <div className="bg-flavor-beetroot/10 border-2 border-flavor-beetroot p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-beetroot rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Beetroot</span>
            </div>
            <div className="bg-flavor-pineapple/10 border-2 border-flavor-pineapple p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-pineapple rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Pineapple</span>
            </div>
            <div className="bg-flavor-hibiscus/10 border-2 border-flavor-hibiscus p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-hibiscus rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Hibiscus</span>
            </div>
            <div className="bg-purple-500/10 border-2 border-purple-500 p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-purple-500 rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Mixed Fruit</span>
            </div>
          </div>

          {/* Login Button */}
          <Button
            data-testid="login-btn"
            onClick={login}
            className="w-full h-14 bg-hh-green text-black hover:bg-green-600 text-lg font-display uppercase tracking-wide border-2 border-black shadow-brutal btn-brutal transition-all"
          >
            {ENABLE_DEV_AUTH ? 'Enter Local Demo' : 'Sign in with Google'}
            <ArrowRight className="ml-2 w-5 h-5" />
          </Button>

          {ENABLE_DEV_AUTH && (
            <div className="mt-4 p-4 border-2 border-black rounded-lg bg-gray-50 space-y-3">
              <p className="text-xs font-display uppercase tracking-wide text-black">Local Dev Sign-In</p>
              {devUsersLoading ? (
                <p className="text-xs text-gray-500">Loading local users...</p>
              ) : devUsers.length > 0 ? (
                <div className="grid gap-2">
                  {devUsers.map((devUser) => (
                  <Button
                    key={devUser.email}
                    data-testid={`dev-login-${devUser.email}`}
                    variant="outline"
                    onClick={() => loginAsDevUser(devUser.email)}
                    className="w-full border-2 border-black justify-between font-display uppercase text-xs"
                  >
                    {getDevUserLabel(devUser)}
                    <span className="normal-case text-[10px]">{devUser.email}</span>
                  </Button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">No local users available. Seed local data first.</p>
              )}
            </div>
          )}

          <p className="text-center text-sm text-gray-500 mt-4">
            Only @5dm.africa emails allowed
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-black text-white p-4 text-center">
        <p className="text-sm">© 2026 5DM Africa. Happy Hour Jaba.</p>
      </footer>
    </div>
  );
};

export default Landing;
