import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { ScrollArea } from '../components/ui/scroll-area';
import { Beer, Phone, FileText, Check } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProfileSetup = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, updateUser } = useAuth();
  const currentUser = location.state?.user || user;

  const [phone, setPhone] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [hasScrolledTerms, setHasScrolledTerms] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollTop + clientHeight >= scrollHeight - 10) {
      setHasScrolledTerms(true);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!hasScrolledTerms) {
      toast.error('Please read through the entire Terms & Conditions');
      return;
    }

    if (!acceptTerms) {
      toast.error('You must accept the Terms & Conditions');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/users/profile-setup`,
        { phone, accept_terms: acceptTerms },
        { withCredentials: true }
      );
      
      updateUser(response.data);
      toast.success('Profile setup complete!');
      navigate('/dashboard', { replace: true, state: { user: response.data } });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to setup profile');
    } finally {
      setLoading(false);
    }
  };

  if (!currentUser) {
    navigate('/', { replace: true });
    return null;
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
            <Beer className="w-6 h-6 text-hh-green" />
          </div>
          <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-black">
            Complete Setup
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6">
        <div className="max-w-md mx-auto">
          {/* Welcome */}
          <div className="text-center mb-6">
            <h2 className="font-display text-2xl uppercase tracking-tight mb-1">
              Welcome, {currentUser?.name?.split(' ')[0]}!
            </h2>
            <p className="text-gray-600 text-sm">
              Complete your profile to start ordering
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Phone Number */}
            <div className="space-y-2">
              <Label htmlFor="phone" className="font-display uppercase text-sm flex items-center gap-2">
                <Phone className="w-4 h-4" />
                Phone Number (Required)
              </Label>
              <Input
                data-testid="phone-input"
                id="phone"
                type="tel"
                placeholder="0712345678"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="h-12 border-2 border-black focus:ring-2 focus:ring-hh-green text-lg"
                required
              />
              <p className="text-xs text-gray-500">
                Kenyan format: 07XXXXXXXX or 01XXXXXXXX
              </p>
            </div>

            {/* Terms & Conditions */}
            <div className="space-y-3">
              <Label className="font-display uppercase text-sm flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Terms & Conditions
              </Label>
              
              <ScrollArea 
                className="h-48 border-2 border-black rounded-lg p-4 bg-gray-50"
                onScrollCapture={handleScroll}
              >
                <div className="text-sm space-y-4 text-gray-700">
                  <h3 className="font-bold">HH Jaba Staff Portal - Terms & Conditions</h3>
                  
                  <p><strong>1. Eligibility</strong><br/>
                  This service is exclusively available to employees of 5DM Africa with valid @5dm.africa email addresses.</p>
                  
                  <p><strong>2. Credit System</strong><br/>
                  - Each employee receives a monthly credit limit of KES 30,000<br/>
                  - Weekly credit limit: 10 bottles per week<br/>
                  - Daily order limit: 5 bottles per day (any payment method)<br/>
                  - Credit balance resets monthly</p>
                  
                  <p><strong>3. Payment</strong><br/>
                  - Credit: Deducted from your monthly allowance<br/>
                  - M-Pesa: Pay to Pam's Airtel (0733 8780020)<br/>
                  - M-Pesa orders require admin verification</p>
                  
                  <p><strong>4. Defaulters Policy</strong><br/>
                  - Outstanding credit balances must be cleared by the 5th of the following month<br/>
                  - Failure to clear balance will result in a 16% VAT penalty<br/>
                  - Penalty = Outstanding Balance × 1.16</p>
                  
                  <p><strong>5. Order Fulfillment</strong><br/>
                  - Orders are subject to stock availability<br/>
                  - Admin reserves the right to reject orders</p>
                  
                  <p><strong>6. Data Privacy</strong><br/>
                  - Your order history is visible to administrators<br/>
                  - Phone numbers are used for order communication only</p>
                  
                  <p><strong>7. Amendments</strong><br/>
                  5DM Africa reserves the right to modify these terms at any time.</p>
                  
                  <p className="pt-4 text-center font-bold text-hh-green">
                    ↓ Scroll to the bottom to continue ↓
                  </p>
                </div>
              </ScrollArea>

              {hasScrolledTerms && (
                <div className="flex items-start gap-3 p-3 bg-hh-green/10 border-2 border-hh-green rounded-lg">
                  <Checkbox
                    data-testid="accept-terms-checkbox"
                    id="terms"
                    checked={acceptTerms}
                    onCheckedChange={setAcceptTerms}
                    className="mt-0.5 border-2 border-black data-[state=checked]:bg-hh-green data-[state=checked]:text-black"
                  />
                  <Label htmlFor="terms" className="text-sm cursor-pointer">
                    I have read and agree to the Terms & Conditions
                  </Label>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button
              data-testid="complete-setup-btn"
              type="submit"
              disabled={loading || !hasScrolledTerms || !acceptTerms}
              className="w-full h-14 bg-hh-green text-black hover:bg-green-600 text-lg font-display uppercase tracking-wide border-2 border-black shadow-brutal btn-brutal transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Setting up...' : (
                <>
                  <Check className="mr-2 w-5 h-5" />
                  Complete Setup
                </>
              )}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ProfileSetup;
