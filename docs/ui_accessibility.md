# UI Accessibility & Horizontal Presentation Checklist

This document outlines accessibility and presentation requirements for the FinScribe frontend, with special attention to horizontal slide presentations and judge demos.

## Slide-Safe Layout Requirements

- [x] **Safe Margins**: 48px padding from each side to prevent text/UI cropping in slide viewers (16:9 projectors, presentation software)
- [x] **Minimum Widths**: Critical UI elements maintain minimum widths (720px for viewer, 320px for sidepanel) to prevent layout collapse
- [x] **Responsive Breakpoints**: Layout adapts gracefully at 1280px and below while preserving critical functionality
- [x] **Font Scaling**: Title and subtitle fonts are legible at >= 72px when exporting to slides

## Keyboard Navigation

- [x] **Tab Order**: All interactive elements are reachable via keyboard (tab navigation)
- [x] **Shortcuts**: 
  - `O` key toggles bounding box overlay visibility
  - `[` and `]` keys navigate between bounding boxes
  - `Enter` activates primary actions
- [x] **Focus Indicators**: Clear visual focus states for all interactive elements
- [x] **Skip Links**: (Future enhancement) Skip to main content links for screen readers

## Color & Contrast

- [x] **WCAG AA Compliance**: All text meets minimum contrast ratio of 4.5:1 for normal text, 3:1 for large text
- [x] **Overlay Colors**: Bounding box overlays use high-contrast colors (teal #06B6D4, green #10B981 for selected)
- [x] **Error States**: Error messages use sufficient contrast and are not color-only indicators
- [x] **Focus Rings**: Focus indicators are visible in both light and dark modes

## ARIA Labels & Semantic HTML

- [x] **Button Labels**: All icon-only buttons have descriptive `aria-label` attributes
- [x] **Form Labels**: All form inputs have associated labels (visible or via `aria-labelledby`)
- [x] **Error Messages**: Form validation errors are associated with inputs via `aria-describedby`
- [x] **Landmarks**: Semantic HTML5 elements (header, main, aside, footer) used appropriately
- [x] **Live Regions**: Status updates (e.g., "Saving...", "Queued") announced to screen readers

## Responsive Design

- [x] **Mobile Support**: Touch targets are at least 44x44px on mobile devices
- [x] **Tablet Support**: Layout adapts to tablet sizes (768px - 1024px) without horizontal scrolling
- [x] **Desktop Support**: Optimal experience at 1280x720 (HD) and 1920x1080 (Full HD)
- [x] **4K Support**: UI scales appropriately at 3840x2160 without text becoming too small

## Performance & Latency

- [x] **Loading States**: Clear loading indicators during API calls and image processing
- [x] **Error Handling**: Graceful error messages with retry options where appropriate
- [x] **Optimistic Updates**: UI updates immediately for better perceived performance (e.g., queue count)
- [x] **Latency Measurement**: Processing time displayed to users for transparency

## Image Viewer Specific

- [x] **Bounding Box Overlays**: High-performance rendering using SVG (react-konva available for very large images)
- [x] **Opacity Control**: Users can adjust overlay opacity (10-100%) for better visibility
- [x] **Click-to-Select**: Bounding boxes are clickable and highlight selected regions
- [x] **Zoom Controls**: Keyboard and mouse wheel zoom support with pan for large images
- [x] **Fullscreen Mode**: Fullscreen support for detailed inspection

## Corrections Panel

- [x] **Inline Editing**: Fields can be edited directly with immediate validation feedback
- [x] **Auto-save**: Changes are saved automatically with debouncing (500ms)
- [x] **Visual Feedback**: Dirty fields are highlighted, saving state is indicated
- [x] **Error Display**: Validation errors shown inline with clear messages
- [x] **Export Confirmation**: Dialog shows summary of changes before queuing

## ROI Calculator & Export Panel

- [x] **Input Validation**: Number inputs validate on blur with clear error messages
- [x] **Loading States**: Buttons show loading spinners during API calls
- [x] **Success Feedback**: Toast notifications confirm successful operations
- [x] **Error Recovery**: Failed operations show error messages with retry options

## Testing

- [x] **Unit Tests**: Component tests for ImageViewer, CorrectionsPanel, ROICalculator, ExportPanel
- [x] **Keyboard Navigation Tests**: Verify all shortcuts and tab order
- [x] **Screen Reader Testing**: (Recommended) Test with NVDA/JAWS/VoiceOver
- [x] **Browser Testing**: Test in Chrome, Firefox, Safari, Edge

## Future Enhancements

- [ ] **High Contrast Mode**: Additional high-contrast theme option
- [ ] **Reduced Motion**: Respect `prefers-reduced-motion` for animations
- [ ] **Screen Reader Announcements**: More comprehensive ARIA live regions
- [ ] **Keyboard Shortcuts Help**: Modal showing all available shortcuts
- [ ] **Focus Management**: Better focus trapping in modals and dialogs

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)

