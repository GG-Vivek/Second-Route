import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, Search, CheckCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import {
  listSKUs,
  lookupSKUBySerial,
  createUnit,
  type SKU,
  type CreateUnitRequest,
  type ReturnReasonCode,
  type OrderChannel,
  RETURN_REASON_CODES,
  ORDER_CHANNELS,
} from '@/api/intake'

interface SKUOption {
  value: string
  label: string
  sku: SKU
}

export function NewIntakePage() {
  const navigate = useNavigate()

  // Form state
  const [serial, setSerial] = useState('')
  const [selectedSKU, setSelectedSKU] = useState<SKUOption | null>(null)
  const [returnReason, setReturnReason] = useState<ReturnReasonCode>('buyer_remorse')
  const [orderChannel, setOrderChannel] = useState<OrderChannel>('online')
  const [notes, setNotes] = useState('')

  // SKU search state
  const [skuSearch, setSkuSearch] = useState('')
  const [filteredSKUs, setFilteredSKUs] = useState<SKUOption[]>([])
  const [showSKUDropdown, setShowSKUDropdown] = useState(false)

  // Serial lookup state
  const [serialLookupLoading, setSerialLookupLoading] = useState(false)
  const [serialLookupError, setSerialLookupError] = useState<string | null>(null)

  // Submit state
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  // Load all SKUs for dropdown
  useEffect(() => {
    async function loadSKUs() {
      try {
        const skus = await listSKUs({ limit: 100 })
        setFilteredSKUs(
          skus.map((sku) => ({
            value: sku.id,
            label: `${sku.family} ${sku.model_name} (${sku.year}) - ${sku.storage_gb}/${sku.ram_gb} ${sku.color}`,
            sku,
          }))
        )
      } catch (err) {
        console.error('Failed to load SKUs:', err)
      }
    }
    loadSKUs()
  }, [])

  // Filter SKUs based on search
  useEffect(() => {
    if (skuSearch) {
      const filtered = filteredSKUs.filter(
        (option) =>
          option.label.toLowerCase().includes(skuSearch.toLowerCase()) ||
          option.sku.family.toLowerCase().includes(skuSearch.toLowerCase()) ||
          option.sku.model_name.toLowerCase().includes(skuSearch.toLowerCase())
      )
      setFilteredSKUs(filtered)
    }
  }, [skuSearch, filteredSKUs])

  // Handle serial lookup
  const handleSerialChange = useCallback(
    async (value: string) => {
      setSerial(value)
      setSerialLookupError(null)

      if (value.length >= 3) {
        setSerialLookupLoading(true)
        try {
          const result = await lookupSKUBySerial(value)
          setSelectedSKU({
            value: result.sku.id,
            label: `${result.sku.family} ${result.sku.model_name} (${result.sku.year}) - ${result.sku.storage_gb}/${result.sku.ram_gb} ${result.sku.color}`,
            sku: result.sku,
          })
          setSerialLookupError(null)
        } catch (err: unknown) {
          const error = err as { response?: { status: number; data?: { detail?: string } } }
          if (error.response?.status === 404) {
            setSerialLookupError('No matching SKU found. Please select manually.')
            setSelectedSKU(null)
          } else {
            setSerialLookupError('Failed to lookup serial')
          }
        } finally {
          setSerialLookupLoading(false)
        }
      } else if (value.length === 0) {
        setSelectedSKU(null)
      }
    },
    []
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)
    setSubmitSuccess(false)

    if (!selectedSKU) {
      setSubmitError('Please select a SKU (or enter a serial number to auto-lookup)')
      return
    }

    setSubmitting(true)
    try {
      const unitData: CreateUnitRequest = {
        sku_id: selectedSKU.value,
        serial: serial || undefined,
        return_reason_code: returnReason,
        order_channel: orderChannel,
      }

      const unit = await createUnit(unitData)
      setSubmitSuccess(true)
      // Redirect to unit detail after brief success message
      setTimeout(() => {
        navigate(`/units/${unit.id}`)
      }, 1500)
    } catch (err: unknown) {
      const error = err as { response?: { status: number; data?: { detail?: string } } }
      if (error.response?.status === 422) {
        setSubmitError('Invalid data. Please check your inputs.')
      } else if (error.response?.status === 404) {
        setSubmitError('SKU not found. Please select a valid SKU.')
      } else {
        setSubmitError('Failed to create unit. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleBack = () => navigate(-1)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={handleBack} className="p-2 rounded-lg hover:bg-accent transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">New Return Intake</h1>
          <p className="text-muted-foreground">Log a returned unit for processing</p>
        </div>
      </div>

      {submitSuccess && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 flex items-center gap-3 text-green-800">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          <span>Unit created successfully! Redirecting...</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Serial Number & SKU Lookup */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">1. Identify Unit</h2>

          {/* Serial Number */}
          <div>
            <label htmlFor="serial" className="block text-sm font-medium mb-1">
              Serial Number <span className="text-muted-foreground">(optional)</span>
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                id="serial"
                type="text"
                value={serial}
                onChange={(e) => handleSerialChange(e.target.value)}
                placeholder="Enter serial number to auto-lookup SKU..."
                className={cn(
                  'w-full pl-10 pr-4 py-2 border rounded-lg bg-background',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
                  'disabled:cursor-not-allowed disabled:opacity-50'
                )}
                disabled={serialLookupLoading || submitting}
              />
              {serialLookupLoading && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
              )}
            </div>
            {serialLookupError && (
              <p className="mt-1 text-sm text-yellow-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {serialLookupError}
              </p>
            )}
          </div>

          {/* SKU Selection */}
          <div>
            <label className="block text-sm font-medium mb-1">
              SKU <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={selectedSKU ? selectedSKU.label : ''}
                onClick={() => setShowSKUDropdown(true)}
                onFocus={() => setShowSKUDropdown(true)}
                readOnly
                placeholder={selectedSKU ? '' : 'Select SKU...'}
                className={cn(
                  'w-full pl-4 pr-10 py-2 border rounded-lg bg-background',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent'
                )}
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              {showSKUDropdown && (
                <div className="absolute z-50 w-full mt-1 border rounded-lg bg-background shadow-lg max-h-60 overflow-auto">
                  {filteredSKUs.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setSelectedSKU(option)
                        setShowSKUDropdown(false)
                        setSkuSearch(option.label)
                      }}
                      className="w-full px-4 py-2 text-left hover:bg-accent first:rounded-t-lg last:rounded-b-lg"
                    >
                      <p className="font-medium">{option.sku.family} {option.sku.model_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {option.sku.year} • {option.sku.storage_gb}/{option.sku.ram_gb} • {option.sku.color} • {option.sku.region}
                      </p>
                    </button>
                  ))}
                  {filteredSKUs.length === 0 && (
                    <div className="px-4 py-2 text-sm text-muted-foreground">No matching SKUs found</div>
                  )}
                </div>
              )}
            </div>
            {!selectedSKU && (
              <p className="mt-1 text-sm text-red-600">Please select a SKU</p>
            )}
          </div>

          {/* Hidden search input for SKU filtering */}
          <input
            type="hidden"
            value={skuSearch}
            onChange={(e) => setSkuSearch(e.target.value)}
          />
        </div>

        {/* Return Reason */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">2. Return Reason</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {RETURN_REASON_CODES.map((reason) => (
              <label
                key={reason.value}
                className={cn(
                  'flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors',
                  returnReason === reason.value
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'hover:border-accent hover:bg-accent/50'
                )}
              >
                <input
                  type="radio"
                  name="returnReason"
                  value={reason.value}
                  checked={returnReason === reason.value}
                  onChange={() => setReturnReason(reason.value)}
                  className="sr-only"
                />
                <span className="font-medium">{reason.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Order Channel */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">3. Order Channel</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {ORDER_CHANNELS.map((channel) => (
              <label
                key={channel.value}
                className={cn(
                  'flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors',
                  orderChannel === channel.value
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'hover:border-accent hover:bg-accent/50'
                )}
              >
                <input
                  type="radio"
                  name="orderChannel"
                  value={channel.value}
                  checked={orderChannel === channel.value}
                  onChange={() => setOrderChannel(channel.value)}
                  className="sr-only"
                />
                <span className="font-medium">{channel.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Notes */}
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">4. Notes (Optional)</h2>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any additional notes about this return..."
            rows={3}
            className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>

        {/* Submit */}
        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            type="button"
            onClick={handleBack}
            className="px-4 py-2 border rounded-lg hover:bg-accent transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !selectedSKU}
            className={cn(
              'ml-auto px-6 py-2 rounded-lg font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Unit'
            )}
          </button>
        </div>

        {submitError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}
      </form>
    </div>
  )
}