import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Beer, ArrowLeft, FileText, Check, Clock, Mail, MessageCircle, Send } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UserInvoices = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [popSubmissions, setPopSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // POP Form State
  const [showPopDialog, setShowPopDialog] = useState(false);
  const [popInvoiceId, setPopInvoiceId] = useState('');
  const [popTransactionCode, setPopTransactionCode] = useState('');
  const [popAmount, setPopAmount] = useState('');
  const [popPaymentMethod, setPopPaymentMethod] = useState('airtel_money');
  const [popPaymentType, setPopPaymentType] = useState('full');
  const [popNotes, setPopNotes] = useState('');

  useEffect(() => {
    fetchInvoices();
    fetchPopSubmissions();
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

  const fetchPopSubmissions = async () => {
    try {
      const response = await axios.get(`${API}/payments/my-submissions`, { withCredentials: true });
      setPopSubmissions(response.data);
    } catch (error) {
      console.error('Failed to fetch POP submissions');
    }
  };

  const submitPop = async () => {
    if (!popInvoiceId || !popTransactionCode || !popAmount) {
      toast.error('Please fill all required fields');
      return;
    }
    try {
      await axios.post(`${API}/payments/submit-pop`, {
        invoice_id: popInvoiceId,
        transaction_code: popTransactionCode.toUpperCase(),
        amount_paid: parseFloat(popAmount),
        payment_method: popPaymentMethod,
        payment_type: popPaymentType,
        notes: popNotes || null
      }, { withCredentials: true });
      toast.success('Payment proof submitted for verification');
      setShowPopDialog(false);
      resetPopForm();
      fetchPopSubmissions();
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit payment proof');
    }
  };

  const resetPopForm = () => {
    setPopInvoiceId('');
    setPopTransactionCode('');
    setPopAmount('');
    setPopPaymentMethod('airtel_money');
    setPopPaymentType('full');
    setPopNotes('');
  };

  const shareViaWhatsApp = (invoice) => {
    const phone = '';
    const text = `Invoice #${invoice.invoice_id}: KES ${invoice.total_amount.toLocaleString()} due. Please pay to Airtel Money 0733878020. Period: ${format(new Date(invoice.billing_period_start), 'MMM dd')} - ${format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}. - Happy Hour Jaba`;
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(text)}`, '_blank');
  };

  const shareViaEmail = (invoice) => {
    const subject = encodeURIComponent(`Invoice ${invoice.invoice_id} - Happy Hour Jaba`);
    const body = encodeURIComponent(`Invoice: ${invoice.invoice_id}\nPeriod: ${format(new Date(invoice.billing_period_start), 'MMM dd, yyyy')} - ${format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}\nTotal: KES ${invoice.total_amount.toLocaleString()}\nStatus: ${invoice.status.toUpperCase()}\n\nPay to: Airtel Money 0733878020\nContact: contact@myhappyhour.co.ke`);
    window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  };

  const getStatusBadge = (status) => {
    const colors = {
      paid: 'bg-hh-green text-black',
      partial: 'bg-blue-500 text-white',
      unpaid: 'bg-red-500 text-white'
    };
    return <Badge className={colors[status] || colors.unpaid}>{status.toUpperCase()}</Badge>;
  };

  const getPopStatus = (invoiceId) => {
    return popSubmissions.filter(p => p.invoice_id === invoiceId);
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
          {/* Payment Info Banner */}
          <div className="p-3 bg-green-50 border-2 border-green-600 rounded-lg text-sm">
            <p className="font-bold text-green-800">Pay to: Airtel Money</p>
            <p className="font-display text-lg text-green-900">0733 878 020</p>
          </div>

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
              {invoices.map((invoice) => {
                const pops = getPopStatus(invoice.invoice_id);
                const hasPendingPop = pops.some(p => p.status === 'pending');
                
                return (
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
                          <span>{item.flavor} x {item.quantity}</span>
                          <span className={item.status === 'paid' ? 'text-green-600' : 'text-red-600'}>
                            KES {item.line_total.toLocaleString()}
                          </span>
                        </div>
                      ))}
                      {invoice.line_items.length > 3 && (
                        <p className="text-xs text-gray-500">+{invoice.line_items.length - 3} more items</p>
                      )}
                    </div>

                    {/* POP Submission Status */}
                    {pops.length > 0 && (
                      <div className="mb-3 space-y-1">
                        {pops.map(pop => (
                          <div key={pop.pop_id} className={`p-2 rounded text-xs flex justify-between items-center ${
                            pop.status === 'approved' ? 'bg-green-50 border border-green-200' :
                            pop.status === 'rejected' ? 'bg-red-50 border border-red-200' :
                            'bg-yellow-50 border border-yellow-200'
                          }`}>
                            <div>
                              <span className="font-medium">{pop.transaction_code}</span>
                              <span className="text-gray-500 ml-2">KES {pop.amount_paid?.toLocaleString()}</span>
                            </div>
                            <Badge className={`text-xs ${
                              pop.status === 'approved' ? 'bg-green-500 text-white' :
                              pop.status === 'rejected' ? 'bg-red-500 text-white' :
                              'bg-yellow-400 text-black'
                            }`}>
                              {pop.status}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                      <p className="font-display text-lg font-bold">
                        KES {invoice.total_amount.toLocaleString()}
                      </p>
                      <div className="flex gap-1">
                        {invoice.status !== 'paid' && !hasPendingPop && (
                          <Button
                            data-testid={`submit-pop-${invoice.invoice_id}`}
                            size="sm"
                            onClick={() => {
                              setPopInvoiceId(invoice.invoice_id);
                              setPopAmount(String(invoice.total_amount));
                              setShowPopDialog(true);
                            }}
                            className="bg-hh-green text-black border-2 border-black text-xs"
                          >
                            <Send className="w-3 h-3 mr-1" />
                            Pay
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => shareViaWhatsApp(invoice)}
                          className="border-2 border-green-600 text-green-600"
                        >
                          <MessageCircle className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => shareViaEmail(invoice)}
                          className="border-2 border-blue-600 text-blue-600"
                        >
                          <Mail className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* POP Submission Dialog */}
      <Dialog open={showPopDialog} onOpenChange={(open) => {
        setShowPopDialog(open);
        if (!open) resetPopForm();
      }}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Submit Payment Proof</DialogTitle>
            <DialogDescription>
              Enter your payment details for Invoice {popInvoiceId}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Payment Info */}
            <div className="p-3 bg-green-50 border-2 border-green-600 rounded-lg">
              <p className="text-sm font-bold text-green-800">Pay to: Airtel Money</p>
              <p className="font-display text-xl text-green-900">0733 878 020</p>
            </div>

            <div>
              <Label className="font-display uppercase text-sm">Transaction Code *</Label>
              <Input
                data-testid="pop-transaction-code"
                value={popTransactionCode}
                onChange={(e) => setPopTransactionCode(e.target.value.toUpperCase())}
                className="border-2 border-black uppercase"
                placeholder="e.g. ABC123XYZ"
              />
            </div>

            <div>
              <Label className="font-display uppercase text-sm">Amount Paid (KES) *</Label>
              <Input
                data-testid="pop-amount"
                type="number"
                value={popAmount}
                onChange={(e) => setPopAmount(e.target.value)}
                className="border-2 border-black"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="font-display uppercase text-sm">Payment Method</Label>
                <Select value={popPaymentMethod} onValueChange={setPopPaymentMethod}>
                  <SelectTrigger data-testid="pop-method" className="border-2 border-black">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="airtel_money">Airtel Money</SelectItem>
                    <SelectItem value="mpesa">M-Pesa</SelectItem>
                    <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="font-display uppercase text-sm">Payment Type</Label>
                <Select value={popPaymentType} onValueChange={setPopPaymentType}>
                  <SelectTrigger data-testid="pop-type" className="border-2 border-black">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full">Full Payment</SelectItem>
                    <SelectItem value="partial">Partial Payment</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="font-display uppercase text-sm">Notes (Optional)</Label>
              <Textarea
                data-testid="pop-notes"
                value={popNotes}
                onChange={(e) => setPopNotes(e.target.value)}
                className="border-2 border-black"
                placeholder="Any additional details..."
              />
            </div>

            <Button
              data-testid="submit-pop-btn"
              onClick={submitPop}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              <Send className="w-4 h-4 mr-2" />
              Submit Payment Proof
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UserInvoices;
