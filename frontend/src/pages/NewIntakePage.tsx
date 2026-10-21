import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, Loader2, Search } from 'lucide-react'
import { cn } from '@/utils/cn'
import {
  Button,
  Callout,
  Field,
  RadioCards,
  StickyActions,
  Step,
  Steps,
  inputClass,
} from '@/components/ui'
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

/**
 * The return intake.
 *
 * A return comes in through a door and has to be written down before
 * anything can happen to it, so the form is three steps and the first
 * one is the slowest: reading the serial and finding the model.
 */
export function NewIntakePage() {
  const navigate = useNavigate()

  const [serial, setSerial] = useState('')
  const [selectedSKU, setSelectedSKU] = useState<SKUOption | null>(null)
  const [returnReason, setReturnReason] = useState<ReturnReasonCode>('buyer_remorse')
  const [orderChannel, setOrderChannel] = useState<OrderChannel>('online')
  const [notes, setNotes] = useState('')

  const [skus, setSkus] = useState<SKUOption[]>([])
  const [skuQuery, setSkuQuery] = useState('')
  const [showSKUDropdown, setShowSKUDropdown] = useState(false)

  const [serialLookupLoading, setSerialLookupLoading] = useState(false)
  const [serialLookupError, setSerialLookupError] = useState<string | null>(null)
  // Counts the lookups, so that a slow answer cannot overwrite a newer
  // one.
  const lookupCounter = useRef(0)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // The catalogue, for the manual choice.
  useEffect(() => {
    async function loadSKUs() {
      try {
        const loaded = await listSKUs({ limit: 100 })
        setSkus(
          loaded.map((sku) => ({
            value: sku.id,
            label: `${sku.family} ${sku.model_name} (${sku.year}) - ${sku.storage_gb}/${sku.ram_gb} ${sku.color}`,
            sku,
          }))
        )
      } catch {
        // The catalogue is a convenience. The serial lookup is the real
        // path, and the operator can still choose by hand.
      }
    }
    void loadSKUs()
  }, [])

  const filteredSKUs = skus.filter((option) => {
    if (!skuQuery) return true
    const needle = skuQuery.toLowerCase()
    return (
      option.label.toLowerCase().includes(needle) ||
      option.sku.family.toLowerCase().includes(needle) ||
      option.sku.model_name.toLowerCase().includes(needle)
    )
  })

  const handleSerialChange = useCallback(async (value: string) => {
    setSerial(value)
    setSerialLookupError(null)

    if (value.length < 3) {
      setSelectedSKU(null)
      return
    }

    // Every keystroke asks the server. The answers can come back in a
    // different order from the questions, and the older one must not
    // overwrite the newer one, or the unit is logged against a model that
    // does not match the serial in the box.
    const asked = ++lookupCounter.current
    setSerialLookupLoading(true)
    try {
      const result = await lookupSKUBySerial(value)
      if (asked !== lookupCounter.current) return
      setSelectedSKU({
        value: result.sku.id,
        label: `${result.sku.family} ${result.sku.model_name} (${result.sku.year}) - ${result.sku.storage_gb}/${result.sku.ram_gb} ${result.sku.color}`,
        sku: result.sku,
      })
    } catch (error: unknown) {
      if (asked !== lookupCounter.current) return
      const apiError = error as { response?: { status: number } }
      if (apiError.response?.status === 404) {
        setSerialLookupError('No matching model was found for that serial. Choose one by hand.')
        setSelectedSKU(null)
      } else {
        setSerialLookupError('The serial could not be looked up.')
      }
    } finally {
      if (asked === lookupCounter.current) {
        setSerialLookupLoading(false)
      }
    }
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitError(null)

    if (!selectedSKU) {
      setSubmitError('Choose a model before logging the return.')
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
      navigate(`/units/${unit.id}`)
    } catch (error: unknown) {
      const apiError = error as { response?: { status: number } }
      if (apiError.response?.status === 422) {
        setSubmitError('The details were not accepted. Check them and try again.')
      } else if (apiError.response?.status === 404) {
        setSubmitError('That model is no longer in the catalogue.')
      } else {
        setSubmitError('The return could not be logged. Try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-3xl space-y-8">
      <div className="flex items-start gap-4">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Log a return</h1>
          <p className="mt-1 text-muted-foreground">
            One return in, one disposition instruction out. Three things to record.
          </p>
        </div>
      </div>

      <Steps>
        <Step
          number={1}
          title="Identify the unit"
          description="Read the serial off the device. The model is looked up from it."
        >
          <div className="space-y-4">
            <Field
              label="Serial number"
              hint="Optional, but it saves looking the model up by hand."
            >
              {({ id, describedBy }) => (
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <input
                    id={id}
                    aria-describedby={describedBy}
                    type="text"
                    value={serial}
                    onChange={(event) => void handleSerialChange(event.target.value)}
                    placeholder="C02XXXXXXXXX"
                    className={cn(inputClass, 'pl-9 pr-9')}
                    disabled={serialLookupLoading || submitting}
                  />
                  {serialLookupLoading && (
                    <Loader2
                      className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
                      aria-hidden="true"
                    />
                  )}
                </div>
              )}
            </Field>

            {serialLookupError && (
              <Callout tone="warning">{serialLookupError}</Callout>
            )}

            <Field
              label="Model"
              required
              error={
                !selectedSKU && serialLookupError
                  ? undefined
                  : undefined
              }
            >
              {({ id }) => (
                <div className="relative">
                  <input
                    id={id}
                    type="text"
                    value={selectedSKU ? selectedSKU.label : skuQuery}
                    onFocus={() => setShowSKUDropdown(true)}
                    onChange={(event) => {
                      setSkuQuery(event.target.value)
                      setShowSKUDropdown(true)
                    }}
                    readOnly={selectedSKU !== null}
                    placeholder="Choose the model"
                    className={inputClass}
                    aria-autocomplete="list"
                    aria-expanded={showSKUDropdown}
                    role="combobox"
                  />
                  {showSKUDropdown && (
                    <div className="absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-2xl border bg-popover p-1 shadow-lg">
                      {filteredSKUs.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => {
                            setSelectedSKU(option)
                            setSkuQuery(option.label)
                            setShowSKUDropdown(false)
                          }}
                          className="w-full rounded-xl px-3 py-2 text-left transition-colors hover:bg-accent"
                        >
                          <span className="block text-sm font-medium">
                            {option.sku.family} {option.sku.model_name}
                          </span>
                          <span className="block text-xs text-muted-foreground">
                            {option.sku.year} &middot; {option.sku.storage_gb}/{
                              option.sku.ram_gb
                            } &middot; {option.sku.color} &middot; {option.sku.region}
                          </span>
                        </button>
                      ))}
                      {filteredSKUs.length === 0 && (
                        <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                          Nothing in the catalogue matches that.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Field>

            {selectedSKU && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-lime" aria-hidden="true" />
                {selectedSKU.sku.family} {selectedSKU.sku.model_name} ({selectedSKU.sku.year})
              </p>
            )}
          </div>
        </Step>

        <Step
          number={2}
          title="Why it came back"
          description="The reason decides which channels are even worth considering."
        >
          <RadioCards
            name="returnReason"
            label="Why the unit came back"
            value={returnReason}
            onChange={setReturnReason}
            options={RETURN_REASON_CODES.map((reason) => ({
              value: reason.value,
              label: reason.label,
            }))}
          />
        </Step>

        <Step
          number={3}
          title="Where it was bought"
          description="The channel the return came in through."
        >
          <div className="space-y-4">
            <RadioCards
              name="orderChannel"
              label="Where the unit was bought"
              value={orderChannel}
              onChange={setOrderChannel}
              options={ORDER_CHANNELS.map((channel) => ({
                value: channel.value,
                label: channel.label,
              }))}
            />

            <Field label="Notes" hint="Anything the next person should know.">
              {({ id, describedBy }) => (
                <textarea
                  id={id}
                  aria-describedby={describedBy}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Any additional notes about this return..."
                  rows={3}
                  className={cn(inputClass, 'resize-y')}
                />
              )}
            </Field>
          </div>
        </Step>
      </Steps>

      {submitError && <Callout tone="caution">{submitError}</Callout>}

      <StickyActions>
        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting || !selectedSKU} className="ml-auto">
          {submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Logging...
            </>
          ) : (
            'Log the return'
          )}
        </Button>
      </StickyActions>
    </form>
  )
}
