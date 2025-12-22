import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCw, Maximize2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export interface BoundingBox {
  id: string;
  x: number; // Normalized 0-1
  y: number; // Normalized 0-1
  width: number; // Normalized 0-1
  height: number; // Normalized 0-1
  label: string;
  confidence?: number;
  fieldType?: 'vendor' | 'invoice_info' | 'line_item' | 'totals' | 'other';
  fieldId?: string; // ID to link to corrections panel
}

interface ImageViewerProps {
  imageUrl: string | null;
  boundingBoxes?: BoundingBox[];
  onBoxClick?: (box: BoundingBox) => void;
  selectedBoxId?: string | null;
  highlightedFieldId?: string | null; // Field ID to highlight on hover
  onFieldHighlight?: (fieldId: string | null) => void;
  isCorrectionMode?: boolean; // When user is actively drawing a new ROI
  className?: string;
}

const BOX_COLORS: Record<string, string> = {
  vendor: 'rgb(20, 184, 166)', // teal
  invoice_info: 'rgb(59, 130, 246)', // blue
  line_item: 'rgb(168, 85, 247)', // purple
  totals: 'rgb(234, 179, 8)', // gold
  other: 'rgb(107, 114, 128)', // gray
};

function ImageViewer({
  imageUrl,
  boundingBoxes = [],
  onBoxClick,
  selectedBoxId,
  highlightedFieldId,
  onFieldHighlight,
  isCorrectionMode = false,
  className,
}: ImageViewerProps) {
  const [showOverlay, setShowOverlay] = useState(true);
  const [opacity, setOpacity] = useState(0.6);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [currentBoxIndex, setCurrentBoxIndex] = useState<number | null>(null);
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Load image and get dimensions
  useEffect(() => {
    if (!imageUrl) {
      setImageLoaded(false);
      return;
    }

    const img = new window.Image();
    img.onload = () => {
      setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
      setImageLoaded(true);
    };
    img.onerror = () => {
      setImageLoaded(false);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!imageLoaded || boundingBoxes.length === 0) return;

      // Toggle overlay with 'o'
      if (e.key === 'o' || e.key === 'O') {
        e.preventDefault();
        setShowOverlay((prev) => !prev);
        return;
      }

      // Navigate boxes with [ and ]
      if (e.key === '[' || e.key === ']') {
        e.preventDefault();
        if (currentBoxIndex === null) {
          setCurrentBoxIndex(0);
          if (onBoxClick && boundingBoxes[0]) {
            onBoxClick(boundingBoxes[0]);
          }
        } else {
          const nextIndex =
            e.key === ']'
              ? (currentBoxIndex + 1) % boundingBoxes.length
              : (currentBoxIndex - 1 + boundingBoxes.length) % boundingBoxes.length;
          setCurrentBoxIndex(nextIndex);
          if (onBoxClick && boundingBoxes[nextIndex]) {
            onBoxClick(boundingBoxes[nextIndex]);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [imageLoaded, boundingBoxes, currentBoxIndex, onBoxClick]);

  // Reset zoom and pan when image changes
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setCurrentBoxIndex(null);
  }, [imageUrl]);

  // Handle mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (!containerRef.current) return;
    e.preventDefault();

    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.5, Math.min(3, zoom * delta));
    setZoom(newZoom);
  }, [zoom]);

  // Handle pan start
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (zoom <= 1) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [zoom, pan]);

  // Handle pan move
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning || zoom <= 1) return;
    setPan({
      x: e.clientX - panStart.x,
      y: e.clientY - panStart.y,
    });
  }, [isPanning, panStart, zoom]);

  // Handle pan end
  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  }, [isFullscreen]);

  // Handle fullscreen change
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  if (!imageUrl) {
    return (
      <div className={cn("flex items-center justify-center bg-muted rounded-lg border-2 border-dashed min-h-[400px]", className)}>
        <div className="text-center text-muted-foreground">
          <EyeOff className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No image to display</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative bg-muted rounded-lg border overflow-hidden", className)}>
      {/* Controls Bar */}
      <div className="absolute top-2 right-2 z-20 flex items-center gap-2 bg-background/90 backdrop-blur-sm rounded-lg p-2 shadow-lg">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setShowOverlay(!showOverlay)}
                aria-label={showOverlay ? 'Hide overlay' : 'Show overlay'}
              >
                {showOverlay ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Toggle overlay (O)</TooltipContent>
          </Tooltip>

          {showOverlay && boundingBoxes.length > 0 && (
            <div className="flex items-center gap-2 px-2">
              <span className="text-xs text-muted-foreground">Opacity:</span>
              <Slider
                value={[opacity * 100]}
                onValueChange={([value]) => setOpacity(value / 100)}
                min={10}
                max={100}
                step={5}
                className="w-20"
                aria-label="Overlay opacity"
              />
            </div>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
                disabled={zoom <= 0.5}
                aria-label="Zoom out"
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Zoom out</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setZoom(Math.min(3, zoom + 0.25))}
                disabled={zoom >= 3}
                aria-label="Zoom in"
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Zoom in</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  setZoom(1);
                  setPan({ x: 0, y: 0 });
                }}
                aria-label="Reset view"
              >
                <RotateCw className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reset view</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={toggleFullscreen}
                aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Image Container */}
      <div
        ref={containerRef}
        className={cn(
          "relative w-full h-full min-h-[400px] overflow-auto",
          isCorrectionMode ? "cursor-crosshair" : "cursor-move"
        )}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          handleMouseUp();
          setHoveredBoxId(null);
        }}
      >
        <div
          className="relative inline-block"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'top left',
          }}
        >
          {!imageLoaded && (
            <div className="flex items-center justify-center w-full h-[400px]">
              <div className="text-center text-muted-foreground">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p>Loading image...</p>
              </div>
            </div>
          )}

          <AnimatePresence>
            {imageLoaded && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="relative"
              >
                <img
                  ref={imageRef}
                  src={imageUrl}
                  alt="Document"
                  className="max-w-full h-auto block"
                  draggable={false}
                />

                {/* Bounding Box Overlay */}
                {showOverlay && boundingBoxes.length > 0 && imageRef.current && (
                  <svg
                    className="absolute top-0 left-0 w-full h-full pointer-events-none"
                    style={{ opacity }}
                  >
                    {boundingBoxes.map((box) => {
                      const isSelected = selectedBoxId === box.id || 
                        (currentBoxIndex !== null && boundingBoxes[currentBoxIndex]?.id === box.id);
                      const isHovered = hoveredBoxId === box.id || 
                        (box.fieldId && highlightedFieldId === box.fieldId);
                      const isHighlighted = isHovered && !isSelected;
                      
                      const color = BOX_COLORS[box.fieldType || 'other'] || BOX_COLORS.other;
                      
                      // Visual states: Correction mode (dashed), Active (solid thick), Hover (semi-transparent thick)
                      let strokeWidth = 2;
                      let strokeDasharray = '4 4';
                      let fillOpacity = 0;
                      
                      if (isCorrectionMode) {
                        // Correction mode: dashed border
                        strokeWidth = 2;
                        strokeDasharray = '6 4';
                      } else if (isSelected) {
                        // Active state: solid thick border with fill
                        strokeWidth = 3;
                        strokeDasharray = '0';
                        fillOpacity = 0.15;
                      } else if (isHovered || isHighlighted) {
                        // Hover state: semi-transparent thick border
                        strokeWidth = 3;
                        strokeDasharray = '0';
                        fillOpacity = 0.08;
                      }

                      return (
                        <g key={box.id}>
                          <rect
                            x={`${box.x * 100}%`}
                            y={`${box.y * 100}%`}
                            width={`${box.width * 100}%`}
                            height={`${box.height * 100}%`}
                            fill={color}
                            fillOpacity={fillOpacity}
                            stroke={color}
                            strokeWidth={strokeWidth}
                            strokeDasharray={strokeDasharray}
                            className={cn(
                              "pointer-events-auto transition-all duration-200",
                              isCorrectionMode ? "cursor-crosshair" : "cursor-pointer"
                            )}
                            onClick={() => {
                              if (onBoxClick && !isCorrectionMode) {
                                onBoxClick(box);
                              }
                            }}
                            onMouseEnter={() => {
                              setHoveredBoxId(box.id);
                              if (box.fieldId && onFieldHighlight) {
                                onFieldHighlight(box.fieldId);
                              }
                            }}
                            onMouseLeave={() => {
                              setHoveredBoxId(null);
                              if (box.fieldId && highlightedFieldId === box.fieldId && onFieldHighlight) {
                                onFieldHighlight(null);
                              }
                            }}
                          />
                          {/* Active label */}
                          {isSelected && !isCorrectionMode && (
                            <text
                              x={`${(box.x + box.width / 2) * 100}%`}
                              y={`${Math.max(box.y * 100 - 4, 12)}%`}
                              textAnchor="middle"
                              className="text-xs font-semibold fill-current"
                              fill={color}
                              style={{
                                filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))',
                                pointerEvents: 'none',
                              }}
                            >
                              Editing: {box.label}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>
                )}

                {/* Hover Tooltips */}
                {showOverlay && boundingBoxes.length > 0 && (
                  <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
                    {boundingBoxes.map((box) => (
                      <TooltipProvider key={box.id}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className="absolute pointer-events-auto cursor-pointer"
                              style={{
                                left: `${box.x * 100}%`,
                                top: `${box.y * 100}%`,
                                width: `${box.width * 100}%`,
                                height: `${box.height * 100}%`,
                              }}
                              onClick={() => {
                                if (onBoxClick) {
                                  onBoxClick(box);
                                }
                              }}
                            />
                          </TooltipTrigger>
                          <TooltipContent>
                            <div className="text-xs">
                              <div className="font-semibold">{box.label}</div>
                              {box.confidence !== undefined && (
                                <div className="text-muted-foreground">
                                  Confidence: {(box.confidence * 100).toFixed(1)}%
                                </div>
                              )}
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Info Badge */}
      {boundingBoxes.length > 0 && (
        <div className="absolute bottom-2 left-2 z-20">
          <Badge variant="secondary" className="bg-background/90 backdrop-blur-sm">
            {boundingBoxes.length} region{boundingBoxes.length > 1 ? 's' : ''} detected
          </Badge>
        </div>
      )}

      {/* Keyboard Shortcuts Hint */}
      {boundingBoxes.length > 0 && (
        <div className="absolute bottom-2 right-2 z-20 hidden md:block">
          <div className="bg-background/90 backdrop-blur-sm rounded-lg p-2 text-xs text-muted-foreground">
            <div>Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">O</kbd> to toggle overlay</div>
            <div>Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">[</kbd> / <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">]</kbd> to navigate</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ImageViewer;

