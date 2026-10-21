import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  Badge,
  Button,
  Callout,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CheckboxGroup,
  CodeBlock,
  Dialog,
  EmptyState,
  Field,
  Kbd,
  Meter,
  RadioCards,
  RangeBar,
  Sheet,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Tooltip,
} from '@/components/ui'

describe('Button', () => {
  it('renders a button that can be pressed', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Accept the recommendation</Button>)

    await userEvent.click(screen.getByRole('button', { name: /accept the recommendation/i }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('does not fire when it is disabled', async () => {
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        Accept
      </Button>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(onClick).not.toHaveBeenCalled()
  })

  it('defaults to type button so it never submits a form by accident', () => {
    render(<Button>Accept</Button>)
    expect(screen.getByRole('button', { name: 'Accept' })).toHaveAttribute('type', 'button')
  })
})

describe('Badge', () => {
  it('shows its text', () => {
    render(<Badge>Synthetic</Badge>)
    expect(screen.getByText('Synthetic')).toBeInTheDocument()
  })
})

describe('Card', () => {
  it('holds a heading and its content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>System status</CardTitle>
        </CardHeader>
        <CardContent>Everything is up.</CardContent>
      </Card>,
    )

    expect(screen.getByRole('heading', { name: 'System status' })).toBeInTheDocument()
    expect(screen.getByText('Everything is up.')).toBeInTheDocument()
  })
})

describe('Callout', () => {
  it('carries the tone in its test id', () => {
    render(<Callout tone="warning">Prices are synthetic.</Callout>)
    expect(screen.getByTestId('callout-warning')).toHaveTextContent('Prices are synthetic.')
  })

  it('renders every tone', () => {
    const tones = ['note', 'tip', 'important', 'warning', 'caution'] as const
    for (const tone of tones) {
      const { unmount } = render(<Callout tone={tone}>Something happened.</Callout>)
      expect(screen.getByTestId(`callout-${tone}`)).toBeInTheDocument()
      unmount()
    }
  })

  it('shows a title when there is one', () => {
    render(
      <Callout tone="caution" title="Prototype">
        <p>Not a money claim.</p>
      </Callout>,
    )
    expect(screen.getByText('Prototype')).toBeInTheDocument()
    expect(screen.getByText('Not a money claim.')).toBeInTheDocument()
  })
})

describe('Field', () => {
  it('labels the control and links the error to it', () => {
    render(
      <Field label="Battery health" error="Must be between 0 and 100" required>
        {({ id, describedBy }) => (
          <input id={id} aria-describedby={describedBy} aria-invalid="true" />
        )}
      </Field>,
    )

    const input = screen.getByLabelText(/battery health/i)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert')).toHaveTextContent('Must be between 0 and 100')
    expect(input.getAttribute('aria-describedby')).toContain('error')
  })

  it('says that a field is required to a screen reader', () => {
    render(
      <Field label="Battery health" required>
        {({ id }) => <input id={id} />}
      </Field>,
    )
    expect(screen.getByText('(required)')).toHaveClass('sr-only')
  })
})

describe('RadioCards', () => {
  const options = [
    { value: 'a', label: 'Buyer remorse' },
    { value: 'b', label: 'Defective' },
  ]

  it('reports the chosen option', async () => {
    const onChange = vi.fn()
    render(
      <RadioCards
        name="reason"
        label="Return reason"
        value="a"
        onChange={onChange}
        options={options}
        data-testid="reason-group"
      />,
    )

    await userEvent.click(screen.getByText('Defective'))
    expect(onChange).toHaveBeenCalledWith('b')
  })

  it('gives the group an accessible name', () => {
    render(
      <RadioCards
        name="reason"
        label="Return reason"
        value="a"
        onChange={vi.fn()}
        options={options}
      />,
    )
    expect(screen.getByRole('radiogroup', { name: 'Return reason' })).toBeInTheDocument()
  })

  it('marks the chosen option as checked', () => {
    render(
      <RadioCards
        name="reason"
        label="Return reason"
        value="b"
        onChange={vi.fn()}
        options={options}
      />,
    )
    expect(screen.getByRole('radio', { name: /defective/i })).toBeChecked()
    expect(screen.getByRole('radio', { name: /buyer remorse/i })).not.toBeChecked()
  })
})

describe('CheckboxGroup', () => {
  it('reports the new map when a box is toggled', async () => {
    const onChange = vi.fn()
    render(
      <CheckboxGroup
        name="tests"
        value={{ display: false, keyboard: false }}
        onChange={onChange}
        options={[
          { key: 'display', label: 'Display' },
          { key: 'keyboard', label: 'Keyboard' },
        ]}
      />,
    )

    await userEvent.click(screen.getByRole('checkbox', { name: /display/i }))
    expect(onChange).toHaveBeenCalledWith({ display: true, keyboard: false })
  })
})

describe('Meter', () => {
  it('reports the value and the range to assistive technology', () => {
    render(<Meter value={0.86} threshold={0.7} />)

    const meter = screen.getByRole('meter')
    expect(meter).toHaveAttribute('aria-valuenow', '86')
    expect(meter).toHaveAttribute('aria-valuemin', '0')
    expect(meter).toHaveAttribute('aria-valuemax', '100')
    expect(screen.getByText('86.0%')).toBeInTheDocument()
  })

  it('clamps a value outside the range', () => {
    render(<Meter value={1.4} />)
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100')
  })
})

describe('RangeBar', () => {
  it('shows the three marks', () => {
    render(<RangeBar low={1000} mid={1200} high={1400} />)

    expect(screen.getByText(/p10 \$1,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/p50 \$1,200\.00/)).toBeInTheDocument()
    expect(screen.getByText(/p90 \$1,400\.00/)).toBeInTheDocument()
  })
})

describe('Tabs', () => {
  it('shows the selected panel and hides the others', () => {
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
        </TabsList>
        <TabsContent value="one">The first panel</TabsContent>
        <TabsContent value="two">The second panel</TabsContent>
      </Tabs>,
    )

    expect(screen.getByText('The first panel')).toBeInTheDocument()
    expect(screen.queryByText('The second panel')).not.toBeInTheDocument()
  })

  it('changes the panel when a tab is pressed', async () => {
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
        </TabsList>
        <TabsContent value="one">The first panel</TabsContent>
        <TabsContent value="two">The second panel</TabsContent>
      </Tabs>,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Two' }))
    expect(screen.getByText('The second panel')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Two' })).toHaveAttribute('aria-selected', 'true')
  })

  it('moves between the tabs with the arrow keys', async () => {
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
        </TabsList>
        <TabsContent value="one">The first panel</TabsContent>
        <TabsContent value="two">The second panel</TabsContent>
      </Tabs>,
    )

    screen.getByRole('tab', { name: 'One' }).focus()
    await userEvent.keyboard('{ArrowRight}')

    expect(screen.getByRole('tab', { name: 'Two' })).toHaveAttribute('aria-selected', 'true')
  })
})

describe('Table', () => {
  it('renders a header and its rows', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Channel</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Open-box</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    )

    expect(screen.getByRole('columnheader', { name: 'Channel' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Open-box' })).toBeInTheDocument()
  })
})

describe('Dialog', () => {
  it('is not in the document when it is closed', () => {
    render(
      <Dialog open={false} onClose={vi.fn()} title="Override">
        <p>The body</p>
      </Dialog>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('is in the document when it is open', () => {
    render(
      <Dialog open onClose={vi.fn()} title="Override">
        <p>The body</p>
      </Dialog>,
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Override')).toBeInTheDocument()
  })

  it('closes when the escape key is pressed', async () => {
    const onClose = vi.fn()
    render(
      <Dialog open onClose={onClose} title="Override">
        <p>The body</p>
      </Dialog>,
    )

    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('closes when the close button is pressed', async () => {
    const onClose = vi.fn()
    render(
      <Dialog open onClose={onClose} title="Override">
        <p>The body</p>
      </Dialog>,
    )

    await userEvent.click(screen.getByRole('button', { name: /close dialog/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

describe('Sheet', () => {
  it('renders its content when it is open', () => {
    render(
      <Sheet open onClose={vi.fn()} title="Filters">
        <p>The filters</p>
      </Sheet>,
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('The filters')).toBeInTheDocument()
  })
})

describe('the smaller pieces', () => {
  it('renders a skeleton', () => {
    const { container } = render(<Skeleton className="h-4 w-20" />)
    expect(container.querySelector('.tw-shimmer')).toBeInTheDocument()
  })

  it('renders an empty state with a way out', () => {
    render(
      <EmptyState
        title="No units found"
        description="Try adjusting your search"
        action={<Button>New unit</Button>}
      />,
    )
    expect(screen.getByText('No units found')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New unit' })).toBeInTheDocument()
  })

  it('renders a tooltip', () => {
    render(
      <Tooltip content="What this does">
        <button type="button">Help</button>
      </Tooltip>,
    )
    expect(screen.getByRole('tooltip')).toHaveTextContent('What this does')
  })

  it('renders a keyboard key', () => {
    render(<Kbd>⌘K</Kbd>)
    expect(screen.getByText('⌘K')).toBeInTheDocument()
  })

  it('renders a code island', () => {
    render(<CodeBlock code="const a = 1" filename="example.ts" />)
    expect(screen.getByText('const a = 1')).toBeInTheDocument()
    expect(screen.getByText('example.ts')).toBeInTheDocument()
  })
})
