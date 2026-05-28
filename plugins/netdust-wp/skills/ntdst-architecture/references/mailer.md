# NTDST Mailer

Template-based email system with queuing support.

**Location:** `app/content/mu-plugins/ntdst-core/services/Mailer.php`

## Global Helpers

All wrapped in `function_exists()` guards.

```php
ntdst_mail()                                    // Get Mailer instance (new per call)
ntdst_send_mail($to, $subject, $message)        // Quick send
ntdst_notify($event, $data)                     // Event notification
ntdst_wrap_email_in_layout($content, $subject)  // Wrap HTML in the framework's layout
```

## Basic Usage

### Simple Email

```php
ntdst_mail()
    ->to('user@example.com')
    ->subject('Hello!')
    ->message('This is a plain text message.')
    ->send();
```

### Template Email

```php
ntdst_mail()
    ->to('user@example.com')
    ->subject('Welcome to Our Platform!')
    ->template('welcome', [
        'name' => 'John',
        'login_url' => home_url('/login'),
    ])
    ->send();
```

### With HTML from Response

```php
$html = ntdst_response()
    ->with('order', $orderData)
    ->with('items', $lineItems)
    ->html('emails/order-confirmation');

ntdst_mail()
    ->to($customer_email)
    ->subject('Order #' . $order_id . ' Confirmed')
    ->html($html)
    ->send();
```

## Fluent Methods

### Recipients

```php
// Single recipient
ntdst_mail()->to('user@example.com');

// Multiple recipients
ntdst_mail()->to(['user1@example.com', 'user2@example.com']);

// CC and BCC
ntdst_mail()
    ->to('main@example.com')
    ->cc('copy@example.com')
    ->bcc('hidden@example.com');

// Reply-to
ntdst_mail()
    ->to('user@example.com')
    ->replyTo('support@example.com');
```

### Content

```php
// Plain text
ntdst_mail()->message('Plain text content');

// HTML
ntdst_mail()->html('<h1>HTML content</h1>');

// Template with data
ntdst_mail()->template('template-name', ['key' => 'value']);
```

### Attachments

`attach()` only accepts files inside the WordPress uploads directory (or other paths allow-listed via the `ntdst_mail_attachment_bases` filter). Paths outside the allow-list are silently refused — the call returns `$this` and a warning is written to the `mail` log. This closes a path-disclosure vector: without the constraint, a caller passing user input could attach `wp-config.php`, `/etc/passwd`, etc.

```php
// Write the PDF to uploads first, then attach.
$upload = wp_upload_dir();
$path = $upload['basedir'] . '/invoices/invoice-' . $order_id . '.pdf';
file_put_contents($path, $pdf_bytes);

ntdst_mail()
    ->to('user@example.com')
    ->subject('Your Invoice')
    ->template('invoice', $data)
    ->attach($path)
    ->send();

// Extend the allow-list (e.g. PDFs generated to a sibling dir of uploads)
add_filter('ntdst_mail_attachment_bases', function ($bases) {
    $bases[] = WP_CONTENT_DIR . '/generated-pdfs';
    return $bases;
});
```

### From Address

```php
ntdst_mail()
    ->from('noreply@example.com', 'My App')
    ->to('user@example.com')
    ->subject('Notification')
    ->send();
```

## Queued Emails

For async sending via WP Cron:

```php
// Send in 1 hour
ntdst_mail()
    ->to($subscribers)
    ->subject('Newsletter')
    ->template('newsletter', $content)
    ->queue(3600);

// Send immediately but async
ntdst_mail()
    ->to('user@example.com')
    ->template('welcome', $data)
    ->queue();
```

## Template Paths

Templates are resolved through `apply_filters('ntdst_mail_template_paths', $paths)`. The default search order:

1. `{child-theme}/views/emails/`
2. `{parent-theme}/views/emails/`
3. `{ntdst-core}/templates/emails/`

The mailer pre-checks that the template file exists across the filter-provided paths *before* delegating to `NTDST_Response::html()`. If no path matches, `getDefaultTemplate()` is used (the message body wrapped in the standard layout). Older code pattern-matched on Response's error-HTML string to detect "template not found" — that fragile coupling has been removed.

```php
// Add a project-specific template directory
add_filter('ntdst_mail_template_paths', function ($paths) {
    $paths[] = STRIDE_CORE_PATH . '/templates/emails';
    return $paths;
});
```

## Header / subject / from sanitization

Defensive CRLF stripping on every input that lands in a header:

- `subject($s)` strips `\r` and `\n`.
- `from($email, $name)` runs `$email` through `sanitize_email()` and strips CRLF from `$name`. If `$name` is empty after stripping, the email is used as the display name.
- `header($name, $value)` strips CRLF from both, and `:` from the name. A name reduced to empty after stripping is dropped silently — no header is emitted.

This closes header-injection paths: `wp_mail()`'s own protection varies by WordPress version, and a CRLF in any of these values can be used to smuggle `Bcc:`, `Set-Cookie:`, etc.

## Email Template Structure

```php
<!-- views/emails/welcome.php -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: sans-serif; padding: 20px;">
    <h1>Welcome, <?php echo esc_html($name); ?>!</h1>

    <p>Thank you for joining us.</p>

    <p>
        <a href="<?php echo esc_url($login_url); ?>"
           style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none;">
            Login to Your Account
        </a>
    </p>
</body>
</html>
```

## Event Notifications

Trigger notification emails based on events:

```php
// Send notification (looks for template matching event name)
ntdst_notify('new_order', [
    'order_id' => $order_id,
    'customer' => $customer_email,
    'total' => $total,
]);

// Register notification handler
add_filter('ntdst/notify/new_order', function($data) {
    ntdst_mail()
        ->to(get_option('admin_email'))
        ->subject('New Order #' . $data['order_id'])
        ->template('admin/new-order', $data)
        ->send();

    ntdst_mail()
        ->to($data['customer'])
        ->subject('Order Confirmation')
        ->template('customer/order-confirmation', $data)
        ->send();
});
```

## Error Handling

```php
$result = ntdst_mail()
    ->to('user@example.com')
    ->subject('Test')
    ->message('Content')
    ->send();

if (is_wp_error($result)) {
    ntdst_log()->error('Email failed', [
        'error' => $result->get_error_message(),
        'to' => 'user@example.com',
    ]);
}
```

## Common Patterns

### Admin Notification

```php
private function notifyAdmin(string $subject, array $data): void
{
    ntdst_mail()
        ->to(get_option('admin_email'))
        ->subject('[Site Alert] ' . $subject)
        ->template('admin/alert', $data)
        ->send();
}
```

### User Welcome Email

```php
public function sendWelcomeEmail(int $user_id): void
{
    $user = get_userdata($user_id);

    ntdst_mail()
        ->to($user->user_email)
        ->subject('Welcome to ' . get_bloginfo('name'))
        ->template('welcome', [
            'name' => $user->display_name,
            'dashboard_url' => home_url('/dashboard'),
        ])
        ->send();
}
```

### Batch Emails with Queue

```php
public function sendNewsletter(array $subscriber_emails, array $content): void
{
    foreach ($subscriber_emails as $email) {
        ntdst_mail()
            ->to($email)
            ->subject($content['subject'])
            ->template('newsletter', $content)
            ->queue(); // Prevents timeout on large lists
    }
}
```

## Default-template substitution

`getDefaultTemplate()` (the fallback used when no template file is found) substitutes `{{key}}` placeholders with values from the data array. **Scalar substitutions are `esc_html()`'d** so user-controlled values can't inject HTML into the email body:

```php
ntdst_mail()
    ->to($user->user_email)
    ->subject('Welcome')
    ->message('Hi {{name}}, welcome to {{site}}.')
    ->send();

// If $user->display_name is '<script>alert(1)</script>', the email body
// contains '&lt;script&gt;alert(1)&lt;/script&gt;' — never raw HTML.
```

For full template files rendered through `template()`, the template author is responsible for escaping (use `esc_html()` / `esc_url()` etc. inside the template).

## Layout wrapping

`ntdst_wrap_email_in_layout($content, $subject)` injects `$content` into the framework's default email layout. The wrapper escapes `$site_name`, `$site_url`, and `$subject` before embedding them — closes XSS-via-blogname (admin-controlled but still untrusted in defense-in-depth). `$content` is treated as HTML by contract.

## Anti-Pattern

```php
// WRONG - bypasses logging, templating, and the CRLF/path/escape hardening
wp_mail($to, $subject, $message);

// CORRECT
ntdst_mail()
    ->to($to)
    ->subject($subject)
    ->message($message)
    ->send();

// WRONG - user-controlled path → potential local file disclosure
ntdst_mail()->attach($_POST['file']);

// CORRECT - generate to uploads, then attach
$path = wp_upload_dir()['basedir'] . '/exports/' . wp_unique_filename(...);
file_put_contents($path, $bytes);
ntdst_mail()->attach($path);
```
