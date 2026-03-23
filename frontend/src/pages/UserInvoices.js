import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Beer, ArrowLeft, FileText, Check, Clock, Share2, Mail } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UserInvoices = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/users/invoices`, { withCredentials: true });
      setInvoices(response.data);
    } catch (error) {
      toast.error('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const shareViaWhatsApp = (invoice) => {
    const text = `*Invoice ${invoice.invoice_id}*%0A%0A` +
      `Customer: ${invoice.customer_name}%0A` +
      `Period: ${format(new Date(invoice.billing_period_start), 'MMM dd')} - ${format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}%0A` +
      `Total: KES ${invoice.total_amount.toLocaleString()}%0A` +
      `Status: ${invoice.status.toUpperCase()}%0A%0A` +
      `Pay to: Airtel Money 0733878020%0A` +
      `Contact: contact@myhappyhour.co.ke`;
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const shareViaEmail = (invoice) => {
    const subject = `Invoice ${invoice.invoice_id} - Happy Hour Jaba`;
    const body = `Invoice ${invoice.invoice_id}%0A%0A` +
      `Customer: ${invoice.customer_name}%0A` +
      `Period: ${format(new Date(invoice.billing_period_start), 'MMM dd')} - ${format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}%0A` +
      `Total: KES ${invoice.total_amount.toLocaleString()}%0A` +
      `Status: ${invoice.status.toUpperCase()}%0A%0A` +
      `Pay to: Airtel Money 0733878020%0A` +
      `Contact: contact@myhappyhour.co.ke`;
    window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  };

  const getStatusBadge = (status) => {
    const colors = {
      paid: 'bg-hh-green text-black',
      partial: 'bg-yellow-500 text-black',
      unpaid: 'bg-red-500 text-white'
    };
    return <Badge className={colors[status] || colors.unpaid}>{status.toUpperCase()}</Badge>;
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4 sticky top-0 z-40">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <Button
            data-testid="back-btn"
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="p-2"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3 flex-1">
            <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
              <Beer className="w-6 h-6 text-hh-green" />
            </div>
            <h1 className="font-display text-xl font-bold uppercase tracking-tight text-black">
              My Invoices
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4">
        <div className="max-w-md mx-auto space-y-4">
          {loading ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-black border-t-hh-green rounded-full animate-spin mx-auto"></div>
            </div>
          ) : invoices.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
              <FileText className="w-12 h-12 mx-auto text-gray-400 mb-3" />
              <p className="text-gray-500">No invoices yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {invoices.map((invoice) => (
                <div
                  key={invoice.invoice_id}
                  data-testid={`invoice-${invoice.invoice_id}`}
                  className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-display font-bold">{invoice.invoice_id}</p>
                      <p className="text-xs text-gray-500">
                        {format(new Date(invoice.billing_period_start), 'MMM dd')} - {format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}
                      </p>
                    </div>
                    {getStatusBadge(invoice.status)}
                  </div>

                  <div className="space-y-1 mb-3 text-sm">
                    {invoice.line_items.slice(0, 3).map((item, idx) => (
                      <div key={idx} className="flex justify-between">
                        <span>{item.flavor} × {item.quantity}</span>
                        <span className={item.status === 'paid' ? 'text-green-600' : 'text-red-600'}>
                          KES {item.line_total.toLocaleString()}
                        </span>
                      </div>
                    ))}
                    {invoice.line_items.length > 3 && (
                      <p className="text-xs text-gray-500">+{invoice.line_items.length - 3} more items</p>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                    <p className="font-display text-lg font-bold">
                      KES {invoice.total_amount.toLocaleString()}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => shareViaWhatsApp(invoice)}
                        className="border-2 border-green-600 text-green-600"
                      >
                        <Share2 className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => shareViaEmail(invoice)}
                        className="border-2 border-blue-600 text-blue-600"
                      >
                        <Mail className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default UserInvoices;
