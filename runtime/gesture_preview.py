"""Draw a proposed touch gesture on a copy of the masked screen."""

import math
from PIL import ImageDraw, ImageFont
from actions import ActionExecutor
from screenshot_image import ScreenshotImage


class GesturePreview:
    @staticmethod
    def render(action, elements, screenshot, *, recorded=False):
        if action.get('argumentError'):
            raise ValueError(action['argumentError'])
        if action['action'] in ('tap', 'demo_tap'):
            if action.get('distance') is not None or action.get('durationMs') is not None or action.get('direction'):
                raise ValueError('demo_tap accepts only a ref or x/y as its target')
            if not action.get('ref') and any(type(action.get(key)) is not int for key in ('x', 'y')):
                raise ValueError('demo_tap coordinates must be integers')
            resolved = ActionExecutor._swipe_arguments(dict(action, direction='right'), elements)
            if 'x' not in resolved:
                raise ValueError('demo_tap requires an explicit ref or x/y target')
            start = (resolved['x'], resolved['y'])
            end = None
        else:
            resolved = ActionExecutor._swipe_arguments(action, elements)
            if recorded:
                GesturePreview._apply_adapter_defaults(resolved, elements)
            if 'distance' not in resolved:
                raise ValueError('demo_swipe requires an explicit target and distance')
            x, y, end_x, end_y = ActionExecutor._swipe_points(resolved, elements)
            start, end = (x, y), (end_x, end_y)

        screen = next(element for element in elements if element.get('type') == 'TestPilotScreenInfo')
        canvas = ScreenshotImage.decode(screenshot)
        scale = (canvas.width / screen['screenWidth'], canvas.height / screen['screenHeight'])

        def pixels(point):
            return tuple(round(value * factor) for value, factor in zip(point, scale))

        draw = ImageDraw.Draw(canvas)
        GesturePreview._draw_coordinate_guides(draw, screen, pixels, canvas.size)
        target_check = ''
        if action.get('expectedRef') and not recorded:
            target_check = GesturePreview._mark_expected_target(draw, action['expectedRef'], elements, start, pixels)
        x, y = pixels(start)
        stroke = max(10, canvas.width // 75)
        radius = 3 * stroke
        outline = stroke + 8
        marker_color = '#ff275b'
        if end is not None:
            tip_x, tip_y = pixels(end)
            angle = math.atan2(tip_y - y, tip_x - x)
            draw.line((x, y, tip_x, tip_y), fill='black', width=outline)
            draw.line((x, y, tip_x, tip_y), fill=marker_color, width=stroke)
            head = [(tip_x, tip_y)]
            for turn in (-0.5, 0.5):
                head.append((tip_x - 2 * radius * math.cos(angle + turn),
                             tip_y - 2 * radius * math.sin(angle + turn)))
            draw.polygon(head, fill=marker_color, outline='black', width=4)
        bounds = (x - radius, y - radius, x + radius, y + radius)
        draw.ellipse(bounds, outline='black', width=outline)
        draw.ellipse(bounds, outline=marker_color, width=stroke)
        draw.line((x - radius // 2, y, x + radius // 2, y), fill='black', width=outline)
        draw.line((x, y - radius // 2, x, y + radius // 2), fill='black', width=outline)
        draw.line((x - radius // 2, y, x + radius // 2, y), fill=marker_color, width=stroke)
        draw.line((x, y - radius // 2, x, y + radius // 2), fill=marker_color, width=stroke)

        gesture = 'tap' if end is None else 'swipe'
        caption = ('Requested gesture on the screenshot from before the action.'
                   if recorded else 'Gesture preview only. No input sent.')
        description = f'{caption} The circle marks the {gesture} start {start}'
        if end is not None:
            description += f' and the arrow points to {end}'
        description += ' in device coordinates. The labelled grid uses the same coordinates.'
        return dict(description=description + target_check, image=ScreenshotImage.encode(canvas))

    @staticmethod
    def _mark_expected_target(draw, ref, elements, start, pixels):
        target = next((element for element in elements if element.get('ref') == ref), None)
        bounds = target.get('coordinates') if target else None
        keys = ('x', 'y', 'width', 'height')
        if not isinstance(bounds, dict) or not all(ActionExecutor._number(bounds.get(key)) for key in keys):
            raise ValueError('expectedRef has no current bounds. Choose a ref from the latest UI evidence.')
        x, y, width, height = (bounds[key] for key in keys)
        if width <= 0 or height <= 0:
            raise ValueError('expectedRef bounds are empty.')
        right, bottom = x + width, y + height
        inside = x <= start[0] < right and y <= start[1] < bottom
        draw.rectangle([pixels((x, y)), pixels((right, bottom))], outline='#14a44d', width=4)
        relation = 'INSIDE' if inside else 'OUTSIDE'
        return (f' Start is {relation} expectedRef {ref} '
                f'(green box, x from {x} to {right}, y from {y} to {bottom}).')

    @staticmethod
    def _draw_coordinate_guides(draw, screen, pixels, size):
        width, height = size
        color = '#0072ba'
        font = ImageFont.load_default(size=max(12, width // 37))
        for axis, limit in enumerate((screen['screenWidth'], screen['screenHeight'])):
            minimum_step = max(1, limit / 14)
            base = 10 ** math.floor(math.log10(minimum_step))
            step = next(base * multiplier for multiplier in (1, 2, 5, 10)
                        if base * multiplier >= minimum_step)
            for value in range(step, math.ceil(limit), step):
                if axis == 0:
                    x, _ = pixels((value, 0))
                    draw.line((x, 0, x, height - 1), fill=color, width=1)
                    draw.text((x + 3, 3), str(value), font=font, fill=color, stroke_width=2, stroke_fill='white')
                else:
                    _, y = pixels((0, value))
                    draw.line((0, y, width - 1, y), fill=color, width=2)
                    draw.text((3, y + 3), str(value), font=font, fill=color, stroke_width=2, stroke_fill='white')

    @staticmethod
    def _apply_adapter_defaults(arguments, elements):
        # Mobile MCP's mobilecli robot uses 400 px for swipe defaults.
        arguments.setdefault('distance', 400)
        if 'x' in arguments:
            return
        screen = next((element for element in elements if element.get('type') == 'TestPilotScreenInfo'), None)
        if not screen:
            raise ValueError('Swipe screen coordinate size is unavailable')
        x, y = math.floor(screen['screenWidth'] / 2), math.floor(screen['screenHeight'] / 2)
        dx, dy = {'right': (-200, 0), 'left': (200, 0), 'down': (0, -200), 'up': (0, 200)}[arguments['direction']]
        arguments.update(x=x + dx, y=y + dy)
