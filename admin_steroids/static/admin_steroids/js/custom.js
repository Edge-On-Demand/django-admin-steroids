(function($){

    function goto_field(name){
        // Expand section if the field's section is currently collapsed.
        var label = $('label[for=id_'+name+']');
        if(!label.is(':visible')){
            var a_el = label.parent().parent().parent().children('h2').children('a');
            a_el.html('Hide');
            a_el.parent().parent().removeClass('collapsed');
        }
        // Scroll to and then highlight the field.
        $('html, body').stop().animate({
                scrollTop: $('label[for=id_'+name+']').parent().offset().top
            },
            1000,
            function(){
                $('label[for=id_'+name+']')
                    .parent()
                    .effect("highlight",
                        {color:'red'},
                        2000,
                        function(){
                            $(this)
                                .stop()
                                .css('background-color','');
                        });
            }
        );
    }
    
    $(document).ready(function($){
        $('.tabular fieldset table').floatHeader();
        $('.results #result_list').floatHeader();
        $('#content table.paleblue').floatHeader();
        
        // Allow hiding of the filter panel.
        var el = $('<a id="changelist-filter-showhide" class="showing" href="#">hide</a>');
        $('#changelist-filter h2').append('&nbsp;');
        $('#changelist-filter h2').append(el);
        function show_filter_panel(el, slow){
            $('#changelist-filter').children().filter(":not(script)").show((slow)?'slow':null);
            el.addClass('showing');
            el.text('hide');
            $.cookie("hide_filter_panel", 'false');
        }
        function hide_filter_panel(el, slow){
            $('#changelist-filter').children().filter(":visible").filter(":not(h2)").hide((slow)?'slow':null);
            el.removeClass('showing');
            el.text('show');
            $.cookie("hide_filter_panel", 'true');
        }
        el.click(function(e){
            var el = $(this);
            if(el.hasClass('showing')){
                hide_filter_panel(el, true);
            }else{
                show_filter_panel(el, true);
            }
            return false;
        });
        if($.cookie("hide_filter_panel") == 'true'){
            hide_filter_panel(el);
        }
        
        // Ensure admin record labels are always visible.
        // Record initial positions of all inline labels.
        $('.module .original p').each(function(i){
            var el = $(this);
            var offset = el.offset();
            el.attr('_left', offset.left);
            el.attr('_top', offset.top);
        });
        // Detect when inline labels become visible.
        $('.module .original p').bind('inview', function (event, visible) {
            var el = $(this);
            if (visible == true){
                el.addClass('_fixed_label');
            } else {
                el.removeClass('_fixed_label');
            }
        });
        // Update labels when the scroll position changes.
        $(window).scroll(function(event) {
            var x = $(this).scrollLeft();
            $('.module .original p._fixed_label').each(function(i){
                var el = $(this);
                el.css('left', x);
            });
        });
        
        // Alert user their capslock is on.
        $('#login-form input').keypress(function(e){
            e = e || window.event;
            var s = String.fromCharCode( e.keyCode || e.which );
            if(s.toUpperCase() === s && s.toLowerCase() !== s && !e.shiftKey){
                $('#caps-lock-warning-text').show();
            }else{
                $('#caps-lock-warning-text').hide();
            }
            return true;
        })
        $('#login-form #id_password').after('<div id="caps-lock-warning-text" style="color:red;display:none;">Your caps lock is on.</div>');
        
        // Auto scroll to field.
        setTimeout(function(){
            if(window.location.hash.slice(0,6) == '#goto_'){
                goto_field(window.location.hash.slice(6));
            }
        }, 1000);
    });
})(jQuery);