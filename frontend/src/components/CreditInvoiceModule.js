import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { 
  Plus, Trash2, FileText, Download, Printer, Check, X, Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FLAVORS = ['Tamarind', 'Watermelon', 'Beetroot', 'Pineapple', 'Hibiscus', 'Mixed Fruit'];
const UNIT_PRICE = 500;

const CreditInvoiceModule = ({ users, onRefresh }) => {
  const [invoices, setInvoices] = useState([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [loading, setLoading] = useState(false);

  // Form state
  const [selectedUser, setSelectedUser] = useState('');
  const [billingStart, setBillingStart] = useState('');
  const [billingEnd, setBillingEnd] = useState('');
  const [lineItems, setLineItems] = useState([{ flavor: '', quantity: 1, status: 'unpaid' }]);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await axios.get(`${API}/admin/credit-invoices`, { withCredentials: true });
      setInvoices(response.data);
    } catch (error) {
      console.error('Failed to fetch invoices');
    }
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { flavor: '', quantity: 1, status: 'unpaid' }]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index));
    }
  };

  const updateLineItem = (index, field, value) => {
    const updated = [...lineItems];
    updated[index][field] = field === 'quantity' ? parseInt(value) || 0 : value;
    setLineItems(updated);
  };

  const calculateTotal = () => {
    return lineItems.reduce((sum, item) => sum + (item.quantity * UNIT_PRICE), 0);
  };

  const resetForm = () => {
    setSelectedUser('');
    setBillingStart('');
    setBillingEnd('');
    setLineItems([{ flavor: '', quantity: 1, status: 'unpaid' }]);
    setNotes('');
  };

  const handleCreateInvoice = async () => {
    if (!selectedUser) {
      toast.error('Please select a customer');
      return;
    }
    if (!billingStart || !billingEnd) {
      toast.error('Please select billing period');
      return;
    }
    if (lineItems.some(item => !item.flavor || item.quantity < 1)) {
      toast.error('Please fill all line items with valid quantities');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/admin/credit-invoices`, {
        user_id: selectedUser,
        billing_period_start: billingStart,
        billing_period_end: billingEnd,
        line_items: lineItems.map(item => ({
          flavor: item.flavor,
          quantity: item.quantity,
          unit_price: UNIT_PRICE,
          status: item.status
        })),
        notes
      }, { withCredentials: true });

      toast.success('Invoice created successfully');
      setShowCreateDialog(false);
      resetForm();
      fetchInvoices();
      
      // Show preview of created invoice
      setSelectedInvoice(response.data);
      setShowPreviewDialog(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create invoice');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (invoiceId, itemIndex, newStatus) => {
    try {
      await axios.put(
        `${API}/admin/credit-invoices/${invoiceId}/line-item/${itemIndex}/status`,
        { status: newStatus },
        { withCredentials: true }
      );
      toast.success('Status updated');
      fetchInvoices();
      
      // Refresh preview if open
      if (selectedInvoice?.invoice_id === invoiceId) {
        const response = await axios.get(`${API}/admin/credit-invoices/${invoiceId}`, { withCredentials: true });
        setSelectedInvoice(response.data);
      }
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleDeleteInvoice = async (invoiceId) => {
    if (!window.confirm('Are you sure you want to delete this invoice?')) return;
    
    try {
      await axios.delete(`${API}/admin/credit-invoices/${invoiceId}`, { withCredentials: true });
      toast.success('Invoice deleted');
      fetchInvoices();
      if (selectedInvoice?.invoice_id === invoiceId) {
        setShowPreviewDialog(false);
        setSelectedInvoice(null);
      }
    } catch (error) {
      toast.error('Failed to delete invoice');
    }
  };

  const printInvoice = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(generateInvoiceHTML(selectedInvoice));
    printWindow.document.close();
    printWindow.print();
  };

  const generateInvoiceHTML = (invoice) => {
    const itemsHTML = invoice.line_items.map(item => `
      <tr>
        <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">${item.flavor}</td>
        <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">${item.quantity}</td>
        <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">KES ${item.unit_price.toLocaleString()}</td>
        <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">KES ${item.line_total.toLocaleString()}</td>
        <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">
          <span style="background: ${item.status === 'paid' ? '#22c55e' : '#ef4444'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">
            ${item.status.toUpperCase()}
          </span>
        </td>
      </tr>
    `).join('');

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Invoice ${invoice.invoice_id}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
          .header { display: flex; justify-content: space-between; border-bottom: 3px solid #22c55e; padding-bottom: 20px; margin-bottom: 30px; }
          .logo { font-size: 28px; font-weight: bold; color: #22c55e; }
          .invoice-title { font-size: 24px; color: #333; }
          .section { margin-bottom: 30px; }
          .section-title { font-size: 14px; color: #666; text-transform: uppercase; margin-bottom: 8px; }
          .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th { background: #000; color: #22c55e; padding: 12px; text-align: left; }
          .total-row { background: #f3f4f6; font-weight: bold; }
          .footer { margin-top: 40px; padding-top: 20px; border-top: 2px solid #000; text-align: center; }
          .payment-box { background: #22c55e; color: #000; padding: 20px; margin-top: 30px; border-radius: 8px; }
          @media print { body { padding: 20px; } }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="logo">HH JABA</div>
          <div style="text-align: right;">
            <div class="invoice-title">CREDIT PURCHASE INVOICE</div>
            <div style="font-size: 18px; font-weight: bold; margin-top: 10px;">${invoice.invoice_id}</div>
          </div>
        </div>

        <div class="info-grid">
          <div class="section">
            <div class="section-title">Bill To</div>
            <div style="font-weight: bold; font-size: 18px;">${invoice.customer_name}</div>
            <div>${invoice.customer_email}</div>
            <div>${invoice.customer_phone || ''}</div>
          </div>
          <div class="section" style="text-align: right;">
            <div class="section-title">Invoice Details</div>
            <div><strong>Date:</strong> ${format(new Date(invoice.created_at), 'MMMM dd, yyyy')}</div>
            <div><strong>Billing Period:</strong></div>
            <div>${format(new Date(invoice.billing_period_start), 'MMM dd, yyyy')} - ${format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Flavor</th>
              <th style="text-align: center;">Qty</th>
              <th style="text-align: right;">Unit Price</th>
              <th style="text-align: right;">Amount</th>
              <th style="text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${itemsHTML}
            <tr class="total-row">
              <td colspan="3" style="padding: 12px; text-align: right; font-size: 18px;">TOTAL AMOUNT</td>
              <td style="padding: 12px; text-align: right; font-size: 18px;">KES ${invoice.total_amount.toLocaleString()}</td>
              <td style="padding: 12px; text-align: center;">
                <span style="background: ${invoice.status === 'paid' ? '#22c55e' : invoice.status === 'partial' ? '#f59e0b' : '#ef4444'}; color: white; padding: 4px 12px; border-radius: 4px;">
                  ${invoice.status.toUpperCase()}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        ${invoice.notes ? `<div class="section" style="margin-top: 20px;"><div class="section-title">Notes</div><div>${invoice.notes}</div></div>` : ''}

        <div class="payment-box">
          <div style="font-weight: bold; font-size: 16px; margin-bottom: 10px;">PAYMENT INSTRUCTIONS</div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div><strong>Method:</strong> ${invoice.payment_method || 'Airtel Money'}</div>
              <div><strong>Number:</strong> ${invoice.payment_number || '0733878020'}</div>
            </div>
            <div style="font-size: 24px; font-weight: bold;">KES ${invoice.total_amount.toLocaleString()}</div>
          </div>
        </div>

        <div class="footer">
          <div style="font-weight: bold;">Happy Hour Jaba - 5DM Africa</div>
          <div style="color: #666;">${invoice.company_email || 'contact@myhappyhour.co.ke'}</div>
          <div style="margin-top: 10px; font-size: 12px; color: #999;">Thank you for your business!</div>
        </div>
      </body>
      </html>
    `;
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl uppercase">Credit Purchase Invoices</h2>
        <Button
          data-testid="create-credit-invoice-btn"
          onClick={() => setShowCreateDialog(true)}
          className="bg-hh-green text-black border-2 border-black shadow-brutal-sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create Invoice
        </Button>
      </div>

      {/* Invoices List */}
      {invoices.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
          <FileText className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <p className="text-gray-500">No credit invoices yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {invoices.map((invoice) => (
            <div
              key={invoice.invoice_id}
              data-testid={`credit-invoice-${invoice.invoice_id}`}
              className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-display font-bold text-lg">{invoice.invoice_id}</p>
                  <p className="text-sm text-gray-600">{invoice.customer_name}</p>
                  <p className="text-xs text-gray-500">
                    {format(new Date(invoice.billing_period_start), 'MMM dd')} - {format(new Date(invoice.billing_period_end), 'MMM dd, yyyy')}
                  </p>
                </div>
                <div className="text-right">
                  {getStatusBadge(invoice.status)}
                  <p className="font-display text-xl font-bold mt-1">
                    KES {invoice.total_amount.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-3">
                {invoice.line_items.map((item, idx) => (
                  <span key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded border">
                    {item.flavor} × {item.quantity}
                    <span className={`ml-1 ${item.status === 'paid' ? 'text-green-600' : 'text-red-600'}`}>
                      ({item.status})
                    </span>
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSelectedInvoice(invoice);
                    setShowPreviewDialog(true);
                  }}
                  className="border-2 border-black"
                >
                  <FileText className="w-4 h-4 mr-1" />
                  View
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDeleteInvoice(invoice.invoice_id)}
                  className="border-2 border-red-500 text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Invoice Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl border-2 border-black shadow-brutal-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Create Credit Purchase Invoice</DialogTitle>
            <DialogDescription>Generate invoice for historical credit purchases</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Customer Selection */}
            <div>
              <Label className="font-display uppercase text-sm">Customer *</Label>
              <Select value={selectedUser} onValueChange={setSelectedUser}>
                <SelectTrigger className="border-2 border-black">
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  {users.map(u => (
                    <SelectItem key={u.user_id} value={u.user_id}>
                      {u.name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Billing Period */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="font-display uppercase text-sm">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Billing Start *
                </Label>
                <Input
                  type="date"
                  value={billingStart}
                  onChange={(e) => setBillingStart(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
              <div>
                <Label className="font-display uppercase text-sm">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Billing End *
                </Label>
                <Input
                  type="date"
                  value={billingEnd}
                  onChange={(e) => setBillingEnd(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
            </div>

            {/* Line Items */}
            <div>
              <Label className="font-display uppercase text-sm mb-2 block">Line Items *</Label>
              <div className="space-y-2">
                {lineItems.map((item, index) => (
                  <div key={index} className="flex gap-2 items-center p-2 bg-gray-50 rounded-lg border">
                    <Select 
                      value={item.flavor} 
                      onValueChange={(v) => updateLineItem(index, 'flavor', v)}
                    >
                      <SelectTrigger className="flex-1 border-2 border-black">
                        <SelectValue placeholder="Select flavor" />
                      </SelectTrigger>
                      <SelectContent>
                        {FLAVORS.map(f => (
                          <SelectItem key={f} value={f}>{f}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    <Input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => updateLineItem(index, 'quantity', e.target.value)}
                      className="w-20 border-2 border-black text-center"
                      placeholder="Qty"
                    />
                    
                    <div className="w-24 text-right font-display font-bold">
                      KES {(item.quantity * UNIT_PRICE).toLocaleString()}
                    </div>

                    <Select 
                      value={item.status} 
                      onValueChange={(v) => updateLineItem(index, 'status', v)}
                    >
                      <SelectTrigger className="w-28 border-2 border-black">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unpaid">Unpaid</SelectItem>
                        <SelectItem value="paid">Paid</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => removeLineItem(index)}
                      disabled={lineItems.length === 1}
                      className="border-2 border-red-500 text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
              
              <Button
                type="button"
                variant="outline"
                onClick={addLineItem}
                className="mt-2 border-2 border-black"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Line Item
              </Button>
            </div>

            {/* Total */}
            <div className="p-4 bg-hh-green/10 border-2 border-hh-green rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-display uppercase">Total Amount</span>
                <span className="font-display text-2xl font-bold">KES {calculateTotal().toLocaleString()}</span>
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label className="font-display uppercase text-sm">Notes (Optional)</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="border-2 border-black"
                placeholder="Additional notes for the invoice..."
              />
            </div>

            {/* Submit */}
            <Button
              data-testid="submit-credit-invoice-btn"
              onClick={handleCreateInvoice}
              disabled={loading}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              {loading ? 'Creating...' : 'Generate Invoice'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Invoice Preview Dialog */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-3xl border-2 border-black shadow-brutal-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">
              Invoice Preview - {selectedInvoice?.invoice_id}
            </DialogTitle>
          </DialogHeader>

          {selectedInvoice && (
            <div className="space-y-4">
              {/* Invoice Header */}
              <div className="flex justify-between items-start p-4 bg-black text-white rounded-lg">
                <div>
                  <h3 className="font-display text-2xl font-bold text-hh-green">HH JABA</h3>
                  <p className="text-sm text-gray-300">Credit Purchase Invoice</p>
                </div>
                <div className="text-right">
                  <p className="font-display text-lg font-bold">{selectedInvoice.invoice_id}</p>
                  <p className="text-sm text-gray-300">
                    {format(new Date(selectedInvoice.created_at), 'MMMM dd, yyyy')}
                  </p>
                </div>
              </div>

              {/* Customer & Period Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-gray-50 rounded-lg border-2 border-black">
                  <p className="text-xs text-gray-500 uppercase mb-1">Bill To</p>
                  <p className="font-bold">{selectedInvoice.customer_name}</p>
                  <p className="text-sm">{selectedInvoice.customer_email}</p>
                  <p className="text-sm">{selectedInvoice.customer_phone}</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg border-2 border-black">
                  <p className="text-xs text-gray-500 uppercase mb-1">Billing Period</p>
                  <p className="font-bold">
                    {format(new Date(selectedInvoice.billing_period_start), 'MMM dd, yyyy')}
                  </p>
                  <p className="text-sm">to</p>
                  <p className="font-bold">
                    {format(new Date(selectedInvoice.billing_period_end), 'MMM dd, yyyy')}
                  </p>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="border-2 border-black rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-black text-hh-green">
                    <tr>
                      <th className="p-3 text-left font-display uppercase">Flavor</th>
                      <th className="p-3 text-center font-display uppercase">Qty</th>
                      <th className="p-3 text-right font-display uppercase">Unit</th>
                      <th className="p-3 text-right font-display uppercase">Amount</th>
                      <th className="p-3 text-center font-display uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedInvoice.line_items.map((item, idx) => (
                      <tr key={idx} className="border-t border-gray-200">
                        <td className="p-3 font-medium">{item.flavor}</td>
                        <td className="p-3 text-center">{item.quantity}</td>
                        <td className="p-3 text-right">KES {item.unit_price.toLocaleString()}</td>
                        <td className="p-3 text-right font-bold">KES {item.line_total.toLocaleString()}</td>
                        <td className="p-3 text-center">
                          <button
                            onClick={() => handleStatusUpdate(
                              selectedInvoice.invoice_id, 
                              idx, 
                              item.status === 'paid' ? 'unpaid' : 'paid'
                            )}
                            className={`px-2 py-1 rounded text-xs font-bold border-2 transition-colors ${
                              item.status === 'paid' 
                                ? 'bg-hh-green text-black border-black' 
                                : 'bg-red-500 text-white border-red-700'
                            }`}
                          >
                            {item.status.toUpperCase()}
                          </button>
                        </td>
                      </tr>
                    ))}
                    <tr className="bg-gray-100 border-t-2 border-black">
                      <td colSpan="3" className="p-3 text-right font-display uppercase font-bold">
                        Total Amount
                      </td>
                      <td className="p-3 text-right font-display text-xl font-bold">
                        KES {selectedInvoice.total_amount.toLocaleString()}
                      </td>
                      <td className="p-3 text-center">
                        {getStatusBadge(selectedInvoice.status)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Payment Info */}
              <div className="p-4 bg-hh-green rounded-lg border-2 border-black">
                <p className="font-display uppercase font-bold mb-2">Payment Instructions</p>
                <div className="flex justify-between items-center">
                  <div>
                    <p><strong>Method:</strong> {selectedInvoice.payment_method || 'Airtel Money'}</p>
                    <p><strong>Number:</strong> {selectedInvoice.payment_number || '0733878020'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm">Amount Due</p>
                    <p className="font-display text-2xl font-bold">
                      KES {selectedInvoice.total_amount.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Company Contact */}
              <div className="text-center text-sm text-gray-600">
                <p className="font-bold">Happy Hour Jaba - 5DM Africa</p>
                <p>{selectedInvoice.company_email || 'contact@myhappyhour.co.ke'}</p>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  onClick={printInvoice}
                  className="flex-1 bg-black text-white border-2 border-black"
                >
                  <Printer className="w-4 h-4 mr-2" />
                  Print / Download PDF
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleDeleteInvoice(selectedInvoice.invoice_id)}
                  className="border-2 border-red-500 text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CreditInvoiceModule;
