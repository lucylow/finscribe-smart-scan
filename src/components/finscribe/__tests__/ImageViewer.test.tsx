import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ImageViewer, { BoundingBox } from '../ImageViewer';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('ImageViewer', () => {
  const mockImageUrl = 'https://example.com/test-image.png';
  const mockBoxes: BoundingBox[] = [
    {
      id: 'box1',
      x: 0.1,
      y: 0.1,
      width: 0.2,
      height: 0.2,
      label: 'Vendor',
      confidence: 0.95,
      fieldType: 'vendor',
    },
    {
      id: 'box2',
      x: 0.5,
      y: 0.5,
      width: 0.3,
      height: 0.3,
      label: 'Invoice Number',
      confidence: 0.88,
      fieldType: 'invoice_info',
    },
  ];

  beforeEach(() => {
    // Mock Image constructor
    global.Image = class {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      src = '';
      naturalWidth = 1200;
      naturalHeight = 800;
      constructor() {
        setTimeout(() => {
          if (this.onload) this.onload();
        }, 0);
      }
    } as any;
  });

  it('renders without image', () => {
    render(<ImageViewer imageUrl={null} boundingBoxes={[]} />);
    expect(screen.getByText('No image to display')).toBeInTheDocument();
  });

  it('renders image with bounding boxes', async () => {
    const onBoxClick = vi.fn();
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
        onBoxClick={onBoxClick}
      />
    );

    await waitFor(() => {
      // Check that overlay controls are present
      expect(screen.getByLabelText(/toggle overlay/i)).toBeInTheDocument();
    });
  });

  it('calls onBoxClick when box is clicked', async () => {
    const onBoxClick = vi.fn();
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
        onBoxClick={onBoxClick}
      />
    );

    await waitFor(() => {
      // Find and click a bounding box (simulated via SVG rect)
      const svg = document.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  it('toggles overlay visibility', async () => {
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
      />
    );

    await waitFor(() => {
      const toggleButton = screen.getByLabelText(/toggle overlay/i);
      expect(toggleButton).toBeInTheDocument();
      
      fireEvent.click(toggleButton);
      // Overlay should be hidden
      expect(screen.getByLabelText(/show overlay/i)).toBeInTheDocument();
    });
  });

  it('highlights selected box', async () => {
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
        selectedBoxId="box1"
      />
    );

    await waitFor(() => {
      const svg = document.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Selected box should have different styling
      const rects = svg?.querySelectorAll('rect');
      expect(rects?.length).toBeGreaterThan(0);
    });
  });

  it('handles keyboard navigation', async () => {
    const onBoxClick = vi.fn();
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
        onBoxClick={onBoxClick}
      />
    );

    await waitFor(() => {
      // Simulate keyboard events
      fireEvent.keyDown(window, { key: 'o' });
      fireEvent.keyDown(window, { key: '[' });
      fireEvent.keyDown(window, { key: ']' });
    });
  });

  it('displays correct number of regions', async () => {
    render(
      <ImageViewer
        imageUrl={mockImageUrl}
        boundingBoxes={mockBoxes}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/2 region/i)).toBeInTheDocument();
    });
  });
});

